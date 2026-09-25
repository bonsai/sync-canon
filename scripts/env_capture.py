#!/usr/bin/env python3
"""env_capture.py — Capture environment state for diff tracking.

Snapshots:
  - hostname, uname, os-release
  - $PATH, $HOME, $SHELL, key env vars
  - Installed packages (pip list, npm list -g, apt list --installed)
  - Git config (user.name, user.email)
  - SSH keys, GPG keys (names only)

Output: .env/<env-id>/{hostname,os-release,env.json,packages.json,...}
"""
import argparse, json, os, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def run(cmd, shell=False):
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""

def capture_env(env_id, out_root):
    out_dir = Path(out_root) / ".env" / env_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    meta = {
        "env_id": env_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    
    # hostname file
    (out_dir / "hostname").write_text(meta["hostname"] + "\n")
    
    # os-release
    if os.path.exists("/etc/os-release"):
        os_release = Path("/etc/os-release").read_text()
        (out_dir / "os-release").write_text(os_release)
        for line in os_release.strip().split("\n"):
            if line.startswith("PRETTY_NAME="):
                meta["os_pretty_name"] = line.split("=", 1)[1].strip('"')
    
    # Environment variables
    env_vars = {}
    for key in ["PATH", "HOME", "SHELL", "USER", "HOME", "XDG_CONFIG_HOME", 
                "SC_DEVICE", "SC_ENV_ID", "SC_DATA_ROOT", "GITHUB_TOKEN",
                "JAVA_HOME", "NODE_PATH", "GOPATH", "RUSTUP_HOME"]:
        val = os.environ.get(key)
        if val:
            env_vars[key] = val
    
    # PATH breakdown
    path_dirs = env_vars.get("PATH", "").split(os.pathsep)
    env_vars["PATH_COUNT"] = len([p for p in path_dirs if p])
    
    (out_dir / "env.json").write_text(json.dumps(env_vars, indent=2, ensure_ascii=False))
    
    # Packages
    packages = {}
    
    # pip
    pip_list = run([sys.executable, "-m", "pip", "list", "--format=json"])
    if pip_list:
        try:
            pip_pkgs = json.loads(pip_list)
            packages["pip"] = [{"name": p["name"], "version": p["version"]} for p in pip_pkgs]
        except Exception:
            pass
    
    # npm (global)
    npm_list = run("npm list -g --depth=0 --json", shell=True)
    if npm_list:
        try:
            npm_data = json.loads(npm_list)
            deps = npm_data.get("dependencies", {})
            packages["npm_global"] = [{"name": k, "version": v.get("version")} for k, v in deps.items()]
        except Exception:
            pass
    
    # apt (if available)
    apt_list = run("apt list --installed 2>/dev/null | head -100", shell=True)
    if apt_list:
        packages["apt"] = apt_list[:2000]  # truncate
    
    (out_dir / "packages.json").write_text(json.dumps(packages, indent=2, ensure_ascii=False))
    
    # Git config
    git_cfg = {}
    for key in ["user.name", "user.email", "init.defaultBranch", "core.editor"]:
        val = run(["git", "config", "--global", key])
        if val:
            git_cfg[key] = val
    (out_dir / "git.json").write_text(json.dumps(git_cfg, indent=2, ensure_ascii=False))
    
    # Summary
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    
    print(f"Captured env: {env_id} → {out_dir}/")
    print(f"  hostname: {meta['hostname']}")
    print(f"  OS: {meta.get('os_pretty_name', meta['platform'])}")
    print(f"  pip packages: {len(packages.get('pip', []))}")
    print(f"  npm packages: {len(packages.get('npm_global', []))}")
    print(f"  PATH dirs: {env_vars.get('PATH_COUNT', 0)}")
    
    return meta

def diff_envs(env1, env2, data_root):
    """Compare two environment captures."""
    d1 = Path(data_root) / ".env" / env1
    d2 = Path(data_root) / ".env" / env2
    
    if not d1.exists() or not d2.exists():
        missing = []
        if not d1.exists(): missing.append(env1)
        if not d2.exists(): missing.append(env2)
        print(f"Missing env data: {', '.join(missing)}")
        return
    
    print(f"=== Diff: {env1} vs {env2} ===\n")
    
    # Meta diff
    m1 = json.loads((d1 / "meta.json").read_text()) if (d1 / "meta.json").exists() else {}
    m2 = json.loads((d2 / "meta.json").read_text()) if (d2 / "meta.json").exists() else {}
    
    print("[Platform]")
    for key in ["hostname", "os_pretty_name", "platform", "machine", "python_version"]:
        v1 = m1.get(key, "-")
        v2 = m2.get(key, "-")
        marker = "  " if v1 == v2 else "≠ "
        print(f"  {marker}{key}: {v1} | {v2}")
    
    # Package diff
    p1 = json.loads((d1 / "packages.json").read_text()) if (d1 / "packages.json").exists() else {}
    p2 = json.loads((d2 / "packages.json").read_text()) if (d2 / "packages.json").exists() else {}
    
    print("\n[Pip packages]")
    s1 = {pkg["name"] for pkg in p1.get("pip", [])}
    s2 = {pkg["name"] for pkg in p2.get("pip", [])}
    only_1 = s1 - s2
    only_2 = s2 - s1
    if only_1:
        print(f"  Only in {env1}: {', '.join(sorted(only_1)[:10])}{' ...' if len(only_1) > 10 else ''}")
    if only_2:
        print(f"  Only in {env2}: {', '.join(sorted(only_2)[:10])}{' ...' if len(only_2) > 10 else ''}")
    if not only_1 and not only_2:
        print(f"  Same packages")
    print(f"  Count: {len(s1)} vs {len(s2)}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    
    cap = sub.add_parser("capture", help="Capture environment state")
    cap.add_argument("env_id", help="Environment ID (e.g. pc1-wsl)")
    cap.add_argument("--out-root", default=os.environ.get("SC_DATA_ROOT", "."))
    
    diff = sub.add_parser("diff", help="Compare two environments")
    diff.add_argument("env1", help="First environment ID")
    diff.add_argument("env2", help="Second environment ID")
    diff.add_argument("--data-root", default=os.environ.get("SC_DATA_ROOT", "."))
    
    args = ap.parse_args()
    
    if args.cmd == "capture":
        capture_env(args.env_id, args.out_root)
    elif args.cmd == "diff":
        diff_envs(args.env1, args.env2, args.data_root)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
