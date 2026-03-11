#!/usr/bin/env python3
"""
Config-driven SSE message forwarder. Watches inbox_pushed.md and forwards new
messages based on ../openwechat_im_client/config.json "forward" section.
Run as a separate process alongside sse_inbox.py. OpenClaw must NOT modify
this script; only config.json is updated when user requests forwarding.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "openwechat_im_client"
CONFIG_PATH = DATA_DIR / "config.json"
INBOX_PATH = DATA_DIR / "inbox_pushed.md"
SSE_LOG_PATH = DATA_DIR / "sse_channel.log"
SEP = "─" * 40


def load_config():
    if not CONFIG_PATH.is_file():
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def log_forward(event: str, **kwargs):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [f"[{ts}]", "FORWARD", event]
    for k, v in kwargs.items():
        parts.append(f"{k}={v}")
    with open(SSE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(" ".join(parts) + "\n")


def parse_message(line: str):
    """Extract sender and content from a message line."""
    line = line.strip()
    if not line or line.startswith("[Disconnected]") or line == SEP:
        return None
    try:
        j = json.loads(line)
        sender = j.get("from") or j.get("sender_id")
        content = j.get("content") or j.get("text") or str(j)
        return {"sender": sender, "content": content, "raw": line}
    except json.JSONDecodeError:
        m = re.match(
            r"\[([^\]]+)\]\s*from=#?(\d+)\(([^)]*)\)\s*type=\w+\s*content=(.*)",
            line,
        )
        if m:
            return {"sender": m.group(2), "content": m.group(4).strip(), "raw": line}
    return None


def forward_webhook(webhook_url: str, msg: dict) -> bool:
    try:
        import requests
    except ImportError:
        log_forward("FORWARD_FAILED", reason="requests_required", method="webhook")
        return False
    try:
        r = requests.post(
            webhook_url,
            json={"sender": msg["sender"], "content": msg["content"]},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log_forward("FORWARD_FAILED", reason=str(e), method="webhook")
        return False


def forward_openclaw_message(channel: str, msg: dict) -> bool:
    try:
        subprocess.run(
            ["openclaw", "message", "send", "--channel", channel, "--content", msg["content"]],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        log_forward("FORWARD_FAILED", reason=str(e), method="openclaw_message")
        return False


def forward_openclaw_agent(msg: dict) -> bool:
    try:
        subprocess.run(
            ["openclaw", "agent", "--deliver", msg["content"]],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        log_forward("FORWARD_FAILED", reason=str(e), method="openclaw_agent")
        return False


def do_forward(cfg: dict, msg: dict) -> bool:
    method = (cfg.get("method") or "webhook").lower()
    if method == "webhook" and cfg.get("webhook_url"):
        return forward_webhook(cfg["webhook_url"], msg)
    if method == "openclaw_message" and cfg.get("channel"):
        return forward_openclaw_message(cfg["channel"], msg)
    if method == "openclaw_agent":
        return forward_openclaw_agent(msg)
    log_forward("FORWARD_SKIP", reason="invalid_config", method=method)
    return False


def main():
    if not INBOX_PATH.exists():
        print(f"{INBOX_PATH} not found. Start sse_inbox.py first.")
        sys.exit(1)

    cfg = load_config()
    fwd = (cfg or {}).get("forward") if cfg else None
    if not fwd or not fwd.get("enabled"):
        print("Forward disabled. Add forward.enabled=true to config.json to enable.")
        sys.exit(0)

    st = INBOX_PATH.stat()
    last_size = st.st_size
    last_mtime = st.st_mtime
    processed_lines = set()
    with open(INBOX_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and line.strip() != SEP and not line.strip().startswith("[Disconnected]"):
                processed_lines.add(hash(line.strip()))
    print("Forwarder running. Watching inbox_pushed.md. Ctrl+C to stop.")

    while True:
        try:
            if not INBOX_PATH.exists():
                time.sleep(2)
                continue
            st = INBOX_PATH.stat()
            if st.st_size != last_size or st.st_mtime != last_mtime:
                with open(INBOX_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line or line == SEP or line.startswith("[Disconnected]"):
                        continue
                    h = hash(line)
                    if h in processed_lines:
                        continue
                    processed_lines.add(h)
                    msg = parse_message(line)
                    if msg:
                        do_forward(fwd, msg)
                last_size = st.st_size
                last_mtime = st.st_mtime

            cfg = load_config()
            fwd = (cfg or {}).get("forward") if cfg else None
            if not fwd or not fwd.get("enabled"):
                print("Forward disabled in config. Exiting.")
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            log_forward("FORWARD_ERROR", reason=str(e))
        time.sleep(1)


if __name__ == "__main__":
    main()
