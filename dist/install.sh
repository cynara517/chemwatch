#!/bin/sh
# ChemWatch portable installer: CLI + standard Agent Skill. macOS / Linux; Python 3.10+.
set -eu
CHEMWATCH_ASSET_BASE=${CHEMWATCH_ASSET_BASE:-https://cynara517.github.io/chemwatch/downloads}
CHEMWATCH_INSTALL_PREFIX=${CHEMWATCH_INSTALL_PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/chemwatch}
CHEMWATCH_BIN_DIR=${CHEMWATCH_BIN_DIR:-$HOME/.local/bin}
CHEMWATCH_SKILL_DIR=${CHEMWATCH_SKILL_DIR:-$HOME/.agents/skills}
agent=codex
while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent) agent=$2; shift 2 ;;
    --prefix) CHEMWATCH_INSTALL_PREFIX=$2; shift 2 ;;
    --bin-dir) CHEMWATCH_BIN_DIR=$2; shift 2 ;;
    --skill-dir) CHEMWATCH_SKILL_DIR=$2; agent=custom; shift 2 ;;
    --help|-h)
      echo 'Usage: install.sh [--agent codex] [--skill-dir HARNESS_SKILLS_ROOT] [--prefix DIR] [--bin-dir DIR]'
      echo 'Installs CLI and skill only. Configure monitoring with chemwatch follow, then watch or a harness scheduler.'
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
if [ "$agent" != codex ] && [ "$agent" != custom ]; then
  echo 'For another harness (including DeepSeek), pass --skill-dir with its actual supported skills root.' >&2
  exit 1
fi
command -v python3 >/dev/null 2>&1 || { echo 'Python 3.10+ is required.' >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo 'curl is required.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { echo 'Python 3.10+ is required.' >&2; exit 1; }
chemwatch_tmp=$(mktemp -d)
trap 'rm -rf "$chemwatch_tmp"' EXIT HUP INT TERM
curl -fsSL --connect-timeout 10 --max-time 45 --retry 2 "${CHEMWATCH_ASSET_BASE%/}/chemwatch-skill.zip" -o "$chemwatch_tmp/skill.zip"
curl -fsSL --connect-timeout 10 --max-time 45 --retry 2 "${CHEMWATCH_ASSET_BASE%/}/skill-manifest.json" -o "$chemwatch_tmp/manifest.json"
python3 - "$chemwatch_tmp/skill.zip" "$chemwatch_tmp/manifest.json" "$CHEMWATCH_INSTALL_PREFIX" "$CHEMWATCH_BIN_DIR" "$CHEMWATCH_SKILL_DIR" <<'PY'
import hashlib,json,os,pathlib,shlex,shutil,stat,sys,tempfile,zipfile
bundle,manifest,prefix,bin_dir,skill_root=map(pathlib.Path,sys.argv[1:])
metadata=json.loads(manifest.read_text())
if hashlib.sha256(bundle.read_bytes()).hexdigest()!=metadata['sha256']:
    raise SystemExit('Bundle checksum mismatch; rerun to fetch a consistent release.')
prefix,bin_dir,skill_root=(p.expanduser().resolve() for p in (prefix,bin_dir,skill_root))
runtime=prefix/'chemwatch-monitor'
skill_link=skill_root/'chemwatch-monitor'
launcher=bin_dir/'chemwatch'
if runtime.exists() and not (runtime/'.chemwatch-managed').is_file():
    raise SystemExit('Refusing to replace an unrelated runtime: '+str(runtime))
if skill_link.is_symlink():
    if skill_link.resolve()!=runtime:
        raise SystemExit('Existing skill points elsewhere: '+str(skill_link))
elif skill_link.exists():
    raise SystemExit('Skill already exists and is not managed by this installer: '+str(skill_link))
if launcher.exists() and '# ChemWatch managed launcher' not in launcher.read_text(errors='ignore'):
    raise SystemExit('Refusing to replace another command: '+str(launcher))
prefix.mkdir(parents=True,exist_ok=True)
staging=pathlib.Path(tempfile.mkdtemp(prefix='.install-',dir=prefix))
try:
    with zipfile.ZipFile(bundle) as archive:
        for item in archive.infolist():
            path=pathlib.PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='chemwatch-monitor' or stat.S_ISLNK(item.external_attr >> 16):
                raise SystemExit('Invalid skill archive path')
        archive.extractall(staging)
    candidate=staging/'chemwatch-monitor'
    if not (candidate/'SKILL.md').is_file() or not (candidate/'scripts/chemwatch.py').is_file():
        raise SystemExit('Skill bundle is incomplete')
    (candidate/'.chemwatch-managed').write_text(metadata['version']+'\n')
    previous=prefix/'.previous-chemwatch-monitor'
    if previous.exists(): shutil.rmtree(previous)
    if runtime.exists(): runtime.rename(previous)
    try: candidate.rename(runtime)
    except BaseException:
        if previous.exists(): previous.rename(runtime)
        raise
    bin_dir.mkdir(parents=True,exist_ok=True)
    skill_root.mkdir(parents=True,exist_ok=True)
    if not skill_link.is_symlink(): skill_link.symlink_to(runtime,target_is_directory=True)
    launcher.write_text('#!/bin/sh\n# ChemWatch managed launcher\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(runtime/'scripts/chemwatch.py'))+' "$@"\n')
    launcher.chmod(0o755)
    if previous.exists(): shutil.rmtree(previous)
finally:
    shutil.rmtree(staging,ignore_errors=True)
print('ChemWatch '+metadata['version']+' installed. No login required.')
print('CLI: '+str(launcher))
print('Skill: '+str(skill_link))
print('Try: '+shlex.quote(str(launcher))+' follow --topic retrosynthesis')
print('Then: '+shlex.quote(str(launcher))+' watch --background')
print('In your AI: use $chemwatch-monitor to monitor the selected topics.')
print('If chemwatch is not on PATH, use the full CLI path above. Installation alone does not start a watcher.')
PY
