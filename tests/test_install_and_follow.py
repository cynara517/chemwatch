"""Exercise installation and monitoring without touching the user's HOME."""
import contextlib
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import chemwatch as cw


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="chemwatch qa ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "subscription.json"
        self.source = cw.ROOT / "dist/data/catalog.json"

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cw.main(list(args))
        return code, output.getvalue()

    def test_follow_then_check_uses_one_persistent_baseline(self):
        code, text = self.cli("follow", "--config", str(self.config), "--source", str(self.source), "--topic", "retrosynthesis", "--no-probe", "--json")
        self.assertEqual((code,json.loads(text)["status"]), (0,"baseline"))
        _, text = self.cli("check", "--config", str(self.config), "--json")
        self.assertEqual(json.loads(text)["status"], "unchanged")
        self.assertEqual(json.loads(text)["selected_count"], len(cw.select(cw.read_json(self.source), ["retrosynthesis"])))

    def test_real_background_watcher_starts_and_stops(self):
        self.cli("follow", "--config", str(self.config), "--source", str(self.source), "--no-probe", "--json")
        cmd = [sys.executable, str(cw.ROOT / "chemwatch.py"), "watch", "--config", str(self.config)]
        result = subprocess.run(cmd + ["--background", "--interval", "60"], capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(result.stdout)["started"])
        heartbeat = self.root / "subscription-watcher/heartbeat.json"
        try:
            deadline = time.monotonic() + 8
            while not heartbeat.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(heartbeat.exists())
            status = subprocess.run(cmd + ["--status"], capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(status.stdout)["running"])
            second = subprocess.run(cmd + ["--background"], capture_output=True, text=True, check=True)
            self.assertIn("already running", second.stdout)
        finally:
            subprocess.run(cmd + ["--stop"], capture_output=True, text=True, check=True)
            time.sleep(5.1)
        status = subprocess.run(cmd + ["--status"], capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(status.stdout)["running"])


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, "scripts/package.py"], cwd=cw.ROOT, check=True, capture_output=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="chemwatch install ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1",0), partial(QuietHandler,directory=str(cw.ROOT / "dist")))
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.env = {**os.environ, "CHEMWATCH_ASSET_BASE":f"http://127.0.0.1:{server.server_port}/downloads", "XDG_STATE_HOME":str(self.root / "state")}
        self.cmd = ["sh",str(cw.ROOT / "install.sh"),"--prefix",str(self.root / "runtime"),"--bin-dir",str(self.root / "bin"),"--skill-dir",str(self.root / "harness skills")]

    def test_install_reinstall_and_cli_work_with_spaces(self):
        subprocess.run(self.cmd,env=self.env,check=True,capture_output=True,text=True)
        launcher = self.root / "bin/chemwatch"
        skill = self.root / "harness skills/chemwatch-monitor"
        self.assertTrue((skill / "SKILL.md").is_file())
        result = subprocess.run([str(launcher),"list","--source",str(cw.ROOT / "dist/data/catalog.json"),"--topic","retrosynthesis","--json"],env=self.env,check=True,capture_output=True,text=True)
        self.assertEqual({r["id"] for r in json.loads(result.stdout)}, {r["id"] for r in cw.select(cw.read_json(cw.ROOT / "dist/data/catalog.json"), ["retrosynthesis"])})
        config = self.root / "state/chemwatch/subscription.json"
        config.parent.mkdir(parents=True,exist_ok=True)
        config.write_text('{"user_preference":"keep me"}')
        subprocess.run(self.cmd,env=self.env,check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(config.read_text())["user_preference"],"keep me")

    def test_refuses_unrelated_skill(self):
        existing = self.root / "harness skills/chemwatch-monitor"
        existing.mkdir(parents=True)
        sentinel = existing / "my-data.txt"
        sentinel.write_text("do not overwrite")
        result = subprocess.run(self.cmd,env=self.env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(sentinel.read_text(),"do not overwrite")

    def test_bundle_matches_authoritative_runtime(self):
        self.assertEqual((cw.ROOT / "chemwatch.py").read_bytes(),(cw.ROOT / "skills/chemwatch-monitor/scripts/chemwatch.py").read_bytes())
        manifest = cw.read_json(cw.ROOT / "dist/downloads/skill-manifest.json")
        self.assertEqual(manifest["sha256"],hashlib.sha256((cw.ROOT / "dist/downloads/chemwatch-skill.zip").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
