#!/usr/bin/env python3
"""
devhub_enum.py — Local Linux Enumeration
=========================================
Targets: Python, Jupyter, MCP servers, open ports,
         history files, credentials, configs, privesc vectors

Usage:
    python3 devhub_enum.py
    python3 devhub_enum.py --output /tmp/enum_out.txt
    python3 devhub_enum.py --section jupyter
    python3 devhub_enum.py --section all

Sections:
    system      Basic OS / user / hostname
    ports       Listening ports and associated processes
    python      Python installs, pip packages, virtualenvs
    jupyter     Jupyter tokens, notebooks, configs, runtime
    mcp         MCP server configs, installs, running processes
    history     Shell / python / node history files
    configs     .env files, config.json, credentials, secrets
    processes   Interesting running processes
    privesc     sudo, SUID, capabilities, writable paths
    npm         Node / npm packages and scripts
"""

import os
import sys
import json
import glob
import socket
import struct
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Colours ──────────────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def banner():
    print(f"""{C.CYAN}{C.BOLD}
 ██████╗ ███████╗██╗   ██╗██╗  ██╗██╗   ██╗██████╗
 ██╔══██╗██╔════╝██║   ██║██║  ██║██║   ██║██╔══██╗
 ██║  ██║█████╗  ██║   ██║███████║██║   ██║██████╔╝
 ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██║██║   ██║██╔══██╗
 ██████╔╝███████╗ ╚████╔╝ ██║  ██║╚██████╔╝██████╔╝
 ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚═════╝
  Local Enumeration — Python / Jupyter / MCP / Privesc
  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{C.RESET}""")

# ─── Output helpers ───────────────────────────────────────────────────────────
OUTPUT_LINES = []

def p(msg="", color="", end="\n"):
    line = f"{color}{msg}{C.RESET}" if color else msg
    print(line, end=end)
    OUTPUT_LINES.append(msg)

def section(title):
    bar = "─" * 60
    p(f"\n{bar}", C.CYAN)
    p(f"  {title}", C.BOLD + C.CYAN)
    p(bar, C.CYAN)

def hit(label, value):
    p(f"  {C.GREEN}[+]{C.RESET} {C.BOLD}{label}:{C.RESET} {value}")

def info(label, value):
    p(f"  {C.BLUE}[*]{C.RESET} {label}: {C.DIM}{value}{C.RESET}")

def warn(label, value):
    p(f"  {C.YELLOW}[!]{C.RESET} {C.BOLD}{label}:{C.RESET} {value}")

def bad(msg):
    p(f"  {C.RED}[-]{C.RESET} {msg}")

def sub(msg):
    p(f"      {C.DIM}{msg}{C.RESET}")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def run(cmd, timeout=8):
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""

def read_file(path):
    try:
        return Path(path).read_text(errors="replace").strip()
    except Exception:
        return None

def file_exists(path):
    return Path(path).exists()

def grep_keywords(filepath, keywords):
    """Return lines from file matching any keyword (case-insensitive)."""
    results = []
    try:
        with open(filepath, errors="replace") as f:
            for i, line in enumerate(f, 1):
                if any(k.lower() in line.lower() for k in keywords):
                    results.append((i, line.rstrip()))
    except Exception:
        pass
    return results

CRED_KEYWORDS = [
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "auth", "credential", "private_key", "access_key", "db_pass",
    "db_password", "jwt", "bearer", "client_secret", "aws_secret",
    "private", "key"
]

# ─── Sections ─────────────────────────────────────────────────────────────────

def enum_system():
    section("SYSTEM INFO")
    hit("Hostname",    run("hostname"))
    hit("Current User", run("whoami"))
    hit("ID",          run("id"))
    hit("OS",          run("uname -a"))
    hit("Distro",      run("cat /etc/os-release | grep PRETTY_NAME").replace('PRETTY_NAME=','').strip('"'))
    hit("Uptime",      run("uptime -p"))
    hit("Date",        run("date"))

    # Other users with shells
    p("\n  [*] Users with shells:", C.BLUE)
    for line in run("cat /etc/passwd | grep -E '(bash|sh|zsh|fish)$'").splitlines():
        sub(line)

    # Groups
    hit("Groups", run("groups"))

    # Home directories visible
    p("\n  [*] Home directories:", C.BLUE)
    for d in Path("/home").iterdir() if Path("/home").exists() else []:
        perm = oct(d.stat().st_mode)[-3:]
        sub(f"{d}  [{perm}]")


def enum_ports():
    section("OPEN PORTS & PROCESSES")

    # /proc/net/tcp — parse raw hex entries for listening sockets
    def parse_proc_net(proto_file):
        entries = []
        try:
            lines = Path(proto_file).read_text().splitlines()[1:]
            for line in lines:
                parts = line.split()
                if len(parts) < 4: continue
                local = parts[1]
                state = parts[3]
                # state 0A = LISTEN
                if state == "0A":
                    addr, port_hex = local.rsplit(":", 1)
                    port = int(port_hex, 16)
                    entries.append(port)
        except Exception:
            pass
        return entries

    tcp4 = parse_proc_net("/proc/net/tcp")
    tcp6 = parse_proc_net("/proc/net/tcp6")
    all_ports = sorted(set(tcp4 + tcp6))

    if all_ports:
        hit("Listening TCP ports", ", ".join(str(p) for p in all_ports))
    else:
        # Fallback to ss
        raw = run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        for line in raw.splitlines():
            sub(line)

    # lsof for process → port mapping
    p("\n  [*] Process → Port mapping:", C.BLUE)
    lsof = run("lsof -i -n -P 2>/dev/null | grep LISTEN")
    if lsof:
        for line in lsof.splitlines():
            sub(line)
    else:
        ss = run("ss -tlnp 2>/dev/null")
        for line in ss.splitlines():
            sub(line)

    # Highlight interesting ports
    interesting = {
        8888: "Jupyter Notebook",
        8080: "HTTP alt / dev server",
        5000: "Flask default",
        3000: "Node/Express default",
        6274: "MCPJam Inspector (CVE-2026-23744)",
        6275: "MCP server alt",
        11434: "Ollama LLM",
        5432: "PostgreSQL",
        3306: "MySQL",
        6379: "Redis",
        27017: "MongoDB",
        2222: "SSH alt",
    }
    found_interesting = [p for p in all_ports if p in interesting]
    if found_interesting:
        p("\n  [!] Interesting ports found:", C.YELLOW)
        for port in found_interesting:
            warn(str(port), interesting[port])


def enum_python():
    section("PYTHON ENVIRONMENT")

    # Python binaries
    for py in ["python3", "python", "python2"]:
        path = run(f"which {py} 2>/dev/null")
        if path:
            ver  = run(f"{py} --version 2>&1")
            hit(py, f"{path}  [{ver}]")

    # pip packages — look for interesting ones
    p("\n  [*] Installed pip packages (filtered):", C.BLUE)
    interesting_pkgs = [
        "jupyter", "notebook", "jupyterlab", "ipython",
        "flask", "django", "fastapi", "uvicorn", "gunicorn",
        "requests", "httpx", "paramiko", "pycrypto", "cryptography",
        "sqlalchemy", "pymysql", "psycopg2", "redis", "pymongo",
        "anthropic", "openai", "langchain", "mcp",
        "boto3", "google-cloud", "azure",
    ]
    pip_list = run("pip3 list 2>/dev/null || pip list 2>/dev/null")
    found_pkgs = []
    for line in pip_list.splitlines():
        name = line.split()[0].lower() if line.split() else ""
        if any(pkg in name for pkg in interesting_pkgs):
            found_pkgs.append(line.strip())
    for pkg in found_pkgs:
        sub(pkg)
    if not found_pkgs:
        bad("No pip output or no interesting packages found")

    # Virtual environments
    p("\n  [*] Virtual environments:", C.BLUE)
    venvs = run(
        "find / -name 'pyvenv.cfg' 2>/dev/null "
        "| grep -v proc | head -20"
    )
    if venvs:
        for v in venvs.splitlines():
            sub(v)
    else:
        bad("No virtualenvs found")

    # Python scripts in common locations
    p("\n  [*] Python scripts in web/app dirs:", C.BLUE)
    scripts = run(
        "find /var/www /opt /srv /app /home -name '*.py' 2>/dev/null "
        "| grep -v __pycache__ | head -30"
    )
    for s in scripts.splitlines():
        sub(s)


def enum_jupyter():
    section("JUPYTER NOTEBOOK")

    # Check if running
    proc = run("ps aux | grep -i jupyter | grep -v grep")
    if proc:
        hit("Process", "RUNNING")
        for line in proc.splitlines():
            sub(line)
    else:
        bad("No Jupyter process found in ps")

    # jupyter CLI
    jup_path = run("which jupyter 2>/dev/null")
    if jup_path:
        hit("Binary", jup_path)
        running = run("jupyter notebook list 2>/dev/null")
        if running:
            warn("Jupyter server list", "")
            for line in running.splitlines():
                sub(line)

    # Runtime files — contain token
    p("\n  [*] Jupyter runtime files (tokens stored here):", C.BLUE)
    runtime_paths = [
        "/home/*/.local/share/jupyter/runtime/nbserver-*.json",
        "/run/user/*/jupyter/nbserver-*.json",
        "/tmp/.jupyter/runtime/nbserver-*.json",
        "/root/.local/share/jupyter/runtime/nbserver-*.json",
    ]
    found_runtime = False
    for pattern in runtime_paths:
        for f in glob.glob(pattern):
            found_runtime = True
            warn("Runtime file", f)
            content = read_file(f)
            if content:
                try:
                    data = json.loads(content)
                    if "token" in data:
                        hit("TOKEN", data["token"])
                    if "url" in data:
                        hit("URL", data["url"])
                    if "port" in data:
                        hit("Port", data["port"])
                except Exception:
                    sub(content[:500])
    if not found_runtime:
        bad("No runtime files found")

    # Config files
    p("\n  [*] Jupyter config files:", C.BLUE)
    config_paths = [
        "/home/*/.jupyter/jupyter_notebook_config.py",
        "/home/*/.jupyter/jupyter_notebook_config.json",
        "/root/.jupyter/jupyter_notebook_config.py",
        "/etc/jupyter/jupyter_notebook_config.py",
    ]
    for pattern in config_paths:
        for f in glob.glob(pattern):
            info("Config", f)
            matches = grep_keywords(f, ["token", "password", "allow_remote", "ip", "open_browser", "NotebookApp"])
            for lineno, line in matches:
                sub(f"L{lineno}: {line}")

    # .ipynb notebooks
    p("\n  [*] Jupyter notebooks (.ipynb):", C.BLUE)
    notebooks = run(
        "find / -name '*.ipynb' 2>/dev/null "
        "| grep -v '.ipynb_checkpoints' | grep -v node_modules | head -30"
    )
    if notebooks:
        for nb in notebooks.splitlines():
            warn("Notebook", nb)
            # Parse notebook for credentials in outputs/source
            content = read_file(nb)
            if content:
                try:
                    data = json.loads(content)
                    cells = data.get("cells", [])
                    for i, cell in enumerate(cells):
                        src = "".join(cell.get("source", []))
                        out_text = ""
                        for out in cell.get("outputs", []):
                            out_text += "".join(out.get("text", []))
                            out_text += "".join(
                                str(x) for x in out.get("data", {}).get("text/plain", [])
                            )
                        combined = src + out_text
                        matches = [
                            kw for kw in CRED_KEYWORDS
                            if kw.lower() in combined.lower()
                        ]
                        if matches:
                            warn(f"  Cell {i} contains keywords", ", ".join(matches))
                            sub(f"Source: {src[:200]}")
                            if out_text:
                                sub(f"Output: {out_text[:200]}")
                except Exception:
                    pass
    else:
        bad("No .ipynb files found")

    # Environment variables related to Jupyter
    p("\n  [*] Jupyter-related env vars:", C.BLUE)
    env = run("env | grep -i jupyter 2>/dev/null")
    for line in env.splitlines():
        sub(line)


def enum_mcp():
    section("MCP (MODEL CONTEXT PROTOCOL)")

    # Running MCP processes
    p("  [*] MCP-related processes:", C.BLUE)
    procs = run("ps aux | grep -iE '(mcp|mcpjam|inspector)' | grep -v grep")
    if procs:
        for line in procs.splitlines():
            warn("Process", line.strip())
    else:
        bad("No MCP processes found in ps")

    # MCPJam Inspector specifically
    p("\n  [*] MCPJam Inspector:", C.BLUE)
    insp = run("which mcpjam-inspector 2>/dev/null || npx mcpjam-inspector --version 2>/dev/null")
    if insp:
        hit("Found", insp)

    # npm global packages
    p("\n  [*] npm global packages (MCP-related):", C.BLUE)
    npm_global = run("npm list -g --depth=0 2>/dev/null")
    for line in npm_global.splitlines():
        if any(k in line.lower() for k in ["mcp", "inspector", "anthropic", "claude", "langchain"]):
            hit("npm global", line.strip())

    # MCP config files
    p("\n  [*] MCP config files:", C.BLUE)
    mcp_patterns = [
        "/home/*/.config/mcp/**/*.json",
        "/home/*/.mcp/**",
        "/etc/mcp/**",
        "/opt/mcp/**",
        "/var/www/**/*mcp*",
        "/home/**/.claude/mcp*.json",
        "/home/**/.config/claude/**",
    ]
    for pattern in mcp_patterns:
        for f in glob.glob(pattern, recursive=True):
            if Path(f).is_file():
                warn("MCP config", f)
                content = read_file(f)
                if content:
                    matches = grep_keywords(f, CRED_KEYWORDS)
                    for lineno, line in matches[:10]:
                        sub(f"L{lineno}: {line}")

    # Port 6274 (MCPJam default)
    p("\n  [*] Port 6274 (MCPJam Inspector default):", C.BLUE)
    port6274 = run("ss -tlnp | grep 6274 2>/dev/null")
    if port6274:
        warn("Port 6274 OPEN", port6274)
    else:
        bad("Port 6274 not listening")

    # /var/www for MCP-related files
    p("\n  [*] MCP-related files in web dirs:", C.BLUE)
    web_mcp = run(
        "find /var/www /opt /srv -type f 2>/dev/null "
        "| xargs grep -l -i 'mcp\\|mcpjam\\|model.*context.*protocol' 2>/dev/null "
        "| head -20"
    )
    for f in web_mcp.splitlines():
        sub(f)


def enum_history():
    section("HISTORY FILES")

    history_files = [
        "~/.bash_history",
        "~/.zsh_history",
        "~/.sh_history",
        "~/.python_history",
        "~/.node_repl_history",
        "~/.mysql_history",
        "~/.psql_history",
        "~/.lesshst",
        "~/.viminfo",
        "~/.config/fish/fish_history",
    ]

    for hf in history_files:
        expanded = os.path.expanduser(hf)
        p_obj    = Path(expanded)
        if p_obj.exists():
            # Check if it's a symlink to /dev/null
            if p_obj.is_symlink():
                target = os.readlink(expanded)
                warn(hf, f"SYMLINK → {target}  (nulled out)")
            elif p_obj.stat().st_size == 0:
                info(hf, "exists but EMPTY (0 bytes)")
            else:
                hit(hf, f"{p_obj.stat().st_size} bytes")
                content = read_file(expanded)
                if content:
                    # Show last 20 lines
                    lines = content.splitlines()[-20:]
                    for line in lines:
                        sub(line)
                    # Check for credentials
                    matches = grep_keywords(expanded, CRED_KEYWORDS)
                    if matches:
                        p("\n  [!] Credential keywords in history:", C.YELLOW)
                        for lineno, line in matches[:10]:
                            warn(f"L{lineno}", line)
        else:
            bad(f"{hf} — not found")

    # /proc/<PID>/environ for current shell — useful if vars were passed
    p("\n  [*] Current process environment (filtered):", C.BLUE)
    pid = os.getpid()
    env_raw = read_file(f"/proc/{pid}/environ")
    if env_raw:
        for entry in env_raw.split("\x00"):
            if any(k.lower() in entry.lower() for k in CRED_KEYWORDS):
                warn("ENV", entry)


def enum_configs():
    section("CONFIG FILES & CREDENTIALS")

    # .env files
    p("  [*] .env files:", C.BLUE)
    env_files = run(
        "find / -name '.env' -o -name '.env.*' -o -name '*.env' 2>/dev/null "
        "| grep -v node_modules | grep -v .git | grep -v proc | head -30"
    )
    for f in env_files.splitlines():
        warn(".env", f)
        content = read_file(f)
        if content:
            for line in content.splitlines():
                if "=" in line and not line.startswith("#"):
                    sub(line)

    # config.json / settings.json / secrets.json
    p("\n  [*] JSON config files:", C.BLUE)
    json_configs = run(
        "find / -name 'config.json' -o -name 'settings.json' "
        "-o -name 'secrets.json' -o -name 'credentials.json' 2>/dev/null "
        "| grep -v node_modules | grep -v proc | grep -v .git | head -20"
    )
    for f in json_configs.splitlines():
        info("JSON", f)
        matches = grep_keywords(f, CRED_KEYWORDS)
        for lineno, line in matches[:5]:
            sub(f"L{lineno}: {line}")

    # SSH keys
    p("\n  [*] SSH keys:", C.BLUE)
    ssh_keys = run(
        "find /home /root /etc/ssh -name 'id_rsa' -o -name 'id_ed25519' "
        "-o -name 'id_ecdsa' -o -name '*.pem' -o -name 'authorized_keys' 2>/dev/null "
        "| head -20"
    )
    for f in ssh_keys.splitlines():
        warn("SSH key", f)
        # Check permissions
        perm = run(f"stat -c '%a %U' {f} 2>/dev/null")
        sub(f"Permissions: {perm}")

    # AWS / cloud credentials
    p("\n  [*] Cloud credential files:", C.BLUE)
    cloud_files = [
        "~/.aws/credentials", "~/.aws/config",
        "~/.gcloud/credentials.db", "~/.config/gcloud/application_default_credentials.json",
        "~/.azure/credentials",
    ]
    for cf in cloud_files:
        expanded = os.path.expanduser(cf)
        if file_exists(expanded):
            warn("Cloud creds", expanded)
            content = read_file(expanded)
            if content:
                sub(content[:500])

    # Web app configs
    p("\n  [*] Web app config files:", C.BLUE)
    web_configs = run(
        "find /var/www /opt /srv /app -name '*.conf' -o -name '*.cfg' "
        "-o -name '*.ini' -o -name '*.yaml' -o -name '*.yml' 2>/dev/null "
        "| grep -v node_modules | head -30"
    )
    for f in web_configs.splitlines():
        matches = grep_keywords(f, CRED_KEYWORDS)
        if matches:
            warn("Config", f)
            for lineno, line in matches[:5]:
                sub(f"L{lineno}: {line}")

    # Database files
    p("\n  [*] Database files:", C.BLUE)
    db_files = run(
        "find / -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' 2>/dev/null "
        "| grep -v proc | grep -v sys | grep -v node_modules | head -20"
    )
    for f in db_files.splitlines():
        size = run(f"du -sh {f} 2>/dev/null | cut -f1")
        sub(f"{f}  [{size}]")


def enum_processes():
    section("RUNNING PROCESSES")

    # Processes running as other users
    p("  [*] Processes NOT running as current user:", C.BLUE)
    me = run("whoami")
    procs = run("ps aux 2>/dev/null")
    for line in procs.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) > 10:
            user, pid, cmd = parts[0], parts[1], parts[10]
            if user != me and user not in ("root", "["):
                sub(f"[{user}] PID {pid}: {cmd[:100]}")

    # Root processes (potential targets)
    p("\n  [*] Root processes (interesting):", C.BLUE)
    interesting_root = run(
        "ps aux | grep root | grep -vE '(\\[|ps |grep |sshd:|/lib/systemd|kthread)' "
        "| grep -v grep | head -20"
    )
    for line in interesting_root.splitlines():
        sub(line[:120])

    # /proc/<PID>/environ for each process — looking for secrets
    p("\n  [*] Scanning /proc environ for credentials:", C.BLUE)
    found_creds = False
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            environ_file = pid_dir / "environ"
            try:
                env_data = environ_file.read_bytes().decode(errors="replace")
                for entry in env_data.split("\x00"):
                    if any(k.lower() in entry.lower() for k in CRED_KEYWORDS):
                        cmdline = read_file(pid_dir / "cmdline") or ""
                        cmdline = cmdline.replace("\x00", " ")[:60]
                        warn(f"PID {pid_dir.name} ({cmdline})", entry[:200])
                        found_creds = True
            except PermissionError:
                pass
    except Exception as e:
        bad(f"Error reading /proc: {e}")
    if not found_creds:
        bad("No credentials found in process environments")


def enum_privesc():
    section("PRIVILEGE ESCALATION VECTORS")

    # sudo -l
    p("  [*] Sudo rights:", C.BLUE)
    sudo_l = run("sudo -l 2>/dev/null")
    if sudo_l:
        for line in sudo_l.splitlines():
            if "NOPASSWD" in line.upper():
                warn("NOPASSWD sudo", line.strip())
            else:
                sub(line)
    else:
        bad("sudo -l returned nothing (no rights or requires password)")

    # SUID binaries
    p("\n  [*] SUID binaries:", C.BLUE)
    suid = run("find / -perm -4000 -type f 2>/dev/null | grep -v proc")
    known_suid = {
        "/usr/bin/sudo", "/usr/bin/passwd", "/usr/bin/newgrp",
        "/usr/bin/gpasswd", "/usr/bin/chfn", "/usr/bin/chsh",
        "/usr/bin/su", "/bin/mount", "/bin/umount", "/bin/su",
        "/usr/lib/openssh/ssh-keysign", "/usr/lib/dbus-1.0/dbus-daemon-launch-helper"
    }
    for f in suid.splitlines():
        if f not in known_suid:
            warn("Unusual SUID", f)
        else:
            sub(f"[standard] {f}")

    # Capabilities
    p("\n  [*] File capabilities:", C.BLUE)
    caps = run("getcap -r / 2>/dev/null | grep -v '^$'")
    if caps:
        for line in caps.splitlines():
            warn("Capability", line)
    else:
        bad("No capabilities found or getcap not available")

    # Writable directories in PATH
    p("\n  [*] Writable directories in PATH:", C.BLUE)
    path_dirs = os.environ.get("PATH", "").split(":")
    for d in path_dirs:
        if os.access(d, os.W_OK):
            warn("Writable PATH dir", d)

    # Cron jobs
    p("\n  [*] Cron jobs:", C.BLUE)
    cron_locations = [
        "/etc/crontab",
        "/etc/cron.d/*",
        "/etc/cron.daily/*",
        "/etc/cron.hourly/*",
        "/var/spool/cron/crontabs/*",
    ]
    for pattern in cron_locations:
        for f in glob.glob(pattern):
            if Path(f).is_file():
                content = read_file(f)
                if content and content.strip():
                    info("Cron", f)
                    for line in content.splitlines():
                        if line.strip() and not line.startswith("#"):
                            sub(line)

    # Writable /etc/passwd or /etc/shadow
    p("\n  [*] Sensitive file permissions:", C.BLUE)
    for f in ["/etc/passwd", "/etc/shadow", "/etc/sudoers"]:
        if file_exists(f):
            writable = os.access(f, os.W_OK)
            if writable:
                warn(f"WRITABLE", f)
            else:
                sub(f"[ok] {f}")

    # Docker socket
    if file_exists("/var/run/docker.sock"):
        warn("Docker socket", "/var/run/docker.sock — check group membership")

    # NFS no_root_squash
    nfs = run("cat /etc/exports 2>/dev/null")
    if nfs and "no_root_squash" in nfs:
        warn("NFS no_root_squash", "/etc/exports")
        sub(nfs)


def enum_npm():
    section("NODE / NPM")

    # npm / node versions
    for bin_ in ["node", "npm", "npx"]:
        path = run(f"which {bin_} 2>/dev/null")
        if path:
            ver = run(f"{bin_} --version 2>/dev/null")
            hit(bin_, f"{path}  [{ver}]")

    # Global packages
    p("\n  [*] Global npm packages:", C.BLUE)
    global_pkgs = run("npm list -g --depth=0 2>/dev/null")
    for line in global_pkgs.splitlines():
        sub(line)

    # package.json in web dirs
    p("\n  [*] package.json files:", C.BLUE)
    pkg_jsons = run(
        "find /var/www /opt /srv /app /home -name 'package.json' 2>/dev/null "
        "| grep -v node_modules | head -20"
    )
    for f in pkg_jsons.splitlines():
        info("package.json", f)
        content = read_file(f)
        if content:
            try:
                data = json.loads(content)
                scripts = data.get("scripts", {})
                if scripts:
                    sub(f"Scripts: {json.dumps(scripts, indent=2)[:300]}")
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                mcp_deps = {k: v for k, v in deps.items() if "mcp" in k.lower() or "claude" in k.lower() or "anthropic" in k.lower()}
                if mcp_deps:
                    warn("MCP/AI deps", str(mcp_deps))
            except Exception:
                pass

    # .npmrc — may contain auth tokens
    p("\n  [*] .npmrc files (auth tokens):", C.BLUE)
    npmrc_files = run("find /home /root /etc -name '.npmrc' 2>/dev/null")
    for f in npmrc_files.splitlines():
        warn(".npmrc", f)
        content = read_file(f)
        if content:
            for line in content.splitlines():
                if "token" in line.lower() or "auth" in line.lower() or "_authToken" in line:
                    warn("Token in .npmrc", line)
                else:
                    sub(line)


# ─── Main ─────────────────────────────────────────────────────────────────────

SECTION_MAP = {
    "system":    enum_system,
    "ports":     enum_ports,
    "python":    enum_python,
    "jupyter":   enum_jupyter,
    "mcp":       enum_mcp,
    "history":   enum_history,
    "configs":   enum_configs,
    "processes": enum_processes,
    "privesc":   enum_privesc,
    "npm":       enum_npm,
}

def main():
    parser = argparse.ArgumentParser(description="devhub_enum.py — Local Linux Enumeration")
    parser.add_argument(
        "--section", "-s",
        default="all",
        choices=list(SECTION_MAP.keys()) + ["all"],
        help="Which section to run (default: all)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save output to file"
    )
    parser.add_argument(
        "--no-banner",
        action="store_true"
    )
    args = parser.parse_args()

    if not args.no_banner:
        banner()

    if args.section == "all":
        for fn in SECTION_MAP.values():
            fn()
    else:
        SECTION_MAP[args.section]()

    p(f"\n{'─'*60}", C.CYAN)
    p(f"  Enumeration complete — {datetime.now().strftime('%H:%M:%S')}", C.CYAN)
    p(f"{'─'*60}\n", C.CYAN)

    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write("\n".join(OUTPUT_LINES))
            p(f"[*] Output saved to {args.output}", C.GREEN)
        except Exception as e:
            p(f"[-] Could not save output: {e}", C.RED)


if __name__ == "__main__":
    main()
