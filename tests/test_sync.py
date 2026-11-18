"""Behavior checks for sync boundaries, network failure and notification retry."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

import chemwatch as cw


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "catalog.json"
        self.data = {"schema_version":"1.0", "entries":[{"id":"a", "name":"Alpha", "kind":"dataset", "family_id":"family", "url":"https://example.org/a", "topics":["retrosynthesis"], "verified_at":"2026-11-17", "monitor":{"type":"github","repo":"example/data"}}]}
        self.save()

    def save(self):
        self.source.write_text(json.dumps(self.data))

    def run_sync(self, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = cw.main(["sync", "--source", str(self.source), "--state-dir", str(self.root / "state"), "--report-dir", str(self.root / "reports"), *extra])
        return code, output.getvalue()

    def report(self, *extra):
        code, text = self.run_sync("--json", *extra)
        return code, json.loads(text)

    def test_initial_baseline_is_not_a_new_discovery_then_unchanged_is_quiet(self):
        code, report = self.report()
        self.assertEqual((code, report["status"], report["added"]), (0,"baseline",[]))
        original = list((self.root / "reports").glob("*.json"))
        self.assertEqual(self.run_sync(), (0,""))
        self.assertEqual(list((self.root / "reports").glob("*.json")), original)

    def test_verified_date_change_is_quiet_but_content_and_removal_are_reported(self):
        self.report()
        self.data["entries"][0]["verified_at"] = "2026-11-18"
        self.save()
        self.assertEqual(self.run_sync(), (0,""))
        self.data["entries"][0]["name"] = "Revised"
        self.save()
        _, report = self.report()
        self.assertEqual(report["changed"][0]["before"]["name"], "Alpha")
        self.data["entries"] = []
        self.save()
        _, report = self.report()
        self.assertEqual(report["removed"][0]["name"], "Revised")

    def test_invalid_remote_content_does_not_destroy_last_good_state(self):
        self.report()
        state = next((self.root / "state").glob("*.json"))
        before = state.read_bytes()
        self.source.write_text("<html>login required</html>")
        self.assertEqual(self.run_sync()[0], 1)
        self.assertEqual(state.read_bytes(), before)

    def test_partial_probe_keeps_good_revision_and_recovers_with_one_signal(self):
        with patch.object(cw, "probe", return_value={"revision":"v1","url":"https://example.org/v1","note":"signal"}):
            self.report("--probe")
        with patch.object(cw, "probe", side_effect=TimeoutError("temporary")):
            code, report = self.report("--probe")
        self.assertEqual(code, 2)
        self.assertEqual(report["observations"]["a"]["revision"], "v1")
        self.assertFalse(report["removed"])
        with patch.object(cw, "probe", return_value={"revision":"v2","url":"https://example.org/v2","note":"signal"}):
            _, report = self.report("--probe")
        self.assertEqual(len(report["upstream_changes"]), 1)

    def test_email_baseline_is_silent_failed_change_is_retried_without_duplicate_event(self):
        with patch.object(cw, "send_email") as sender:
            self.report("--email", "test@example.org")
            sender.assert_not_called()
        self.data["entries"][0]["name"] = "Changed"
        self.save()
        with patch.object(cw, "send_email", side_effect=OSError("SMTP unavailable")):
            code, report = self.report("--email", "test@example.org")
        self.assertEqual((code, report["status"]), (2,"notification_error"))
        with patch.object(cw, "send_email") as sender:
            _, report = self.report("--email", "test@example.org")
            sender.assert_called_once()
            self.assertEqual(report["status"], "unchanged")
        with patch.object(cw, "send_email") as sender:
            self.report("--email", "test@example.org")
            sender.assert_not_called()

    def test_source_and_topic_filters_have_separate_baselines(self):
        self.report()
        _, report = self.report("--topic", "retrosynthesis")
        self.assertTrue(report["baseline"])
        self.assertEqual(report["selected_count"], 1)
        self.assertEqual(len(list((self.root / "state").glob("*.json"))), 2)

    def test_remote_catalog_addition_syncs_over_http(self):
        payload = [json.dumps(self.data).encode()]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload[0])
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.source = f"http://127.0.0.1:{server.server_port}/catalog.json"
        self.report()
        e = copy.deepcopy(self.data["entries"][0]);e["id"]="b";e["name"]="Beta"
        self.data["entries"].append(e)
        payload[0] = json.dumps(self.data).encode()
        _, report = self.report()
        self.assertEqual([e["id"] for e in report["added"]], ["b"])

    def test_catalog_seed_ids_and_topic_contract(self):
        data = cw.validate_catalog(cw.read_json(cw.ROOT / "dist/data/catalog.json"))
        self.assertEqual(len({e["id"] for e in data["entries"]}), len(data["entries"]))
        self.assertTrue(all(set(e["topics"]) <= cw.TOPICS for e in data["entries"]))
        retro = cw.select(data,["retrosynthesis"])
        self.assertEqual({e["family_id"] for e in retro if e["id"].startswith("uspto-")}, {"uspto"})
        industrial = cw.select(data,["penicillin","erythromycin"])
        self.assertEqual(len(industrial), 2)

    def test_zenodo_latest_schema_and_file_changes(self):
        record = {"id":123, "metadata":{"version":"v1"}, "files":[{"key":"data.csv","checksum":"md5:a"}], "links":{"self_html":"https://zenodo.org/records/123", "latest":"https://zenodo.org/api/records/123/versions/latest"}, "modified":"2026-01-01"}
        entry = {"monitor":{"type":"zenodo","record":"123"}}
        with patch.object(cw, "api_json", return_value=record):
            first = cw.probe(entry)
            self.assertEqual(first["url"], record["links"]["self_html"])
            record["modified"] = "2026-02-01"
            self.assertEqual(cw.probe(entry)["revision"], first["revision"])
            record["files"][0]["checksum"] = "md5:b"
            self.assertNotEqual(cw.probe(entry)["revision"], first["revision"])


if __name__ == "__main__":
    unittest.main()
