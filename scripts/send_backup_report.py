#!/usr/bin/env python3
import argparse
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_DIR = Path("/var/backups/kitaly")
DEFAULT_LOG_PATH = Path("/var/log/kitaly_backup.log")


def load_env(path):
    values = {}
    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def tail(path, max_lines=80):
    if not path.exists():
        return "No log file found yet."
    lines = path.read_text(errors="replace").splitlines()
    return "\n".join(lines[-max_lines:]) or "Log file is empty."


def build_report(backup_dir, log_path):
    backups = sorted(backup_dir.glob("kitaly_backup_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    now = datetime.now(timezone.utc)
    newest = backups[0] if backups else None
    newest_age_hours = None
    if newest:
        newest_age_hours = (now.timestamp() - newest.stat().st_mtime) / 3600

    lines = [
        "Kitaly backup weekly status",
        f"Generated at: {now.isoformat()}",
        f"Backup directory: {backup_dir}",
        f"Backup count: {len(backups)}",
    ]
    if newest:
        lines.extend(
            [
                f"Latest backup: {newest.name}",
                f"Latest backup size: {newest.stat().st_size / (1024 * 1024):.2f} MB",
                f"Latest backup age: {newest_age_hours:.1f} hours",
            ]
        )
    else:
        lines.append("Latest backup: NONE")

    lines.extend(["", "Recent backup log:", tail(log_path)])
    status_ok = bool(newest and newest_age_hours is not None and newest_age_hours <= 48)
    return status_ok, "\n".join(lines)


def send_email(env, recipient, subject, body):
    host = env.get("SMTP_HOST")
    port = int(env.get("SMTP_PORT") or 587)
    username = env.get("SMTP_USER")
    password = env.get("SMTP_PASSWORD")
    sender = env.get("SMTP_FROM") or username or env.get("OFFICIAL_EMAIL")
    use_tls = (env.get("SMTP_USE_TLS") or "true").lower() not in {"0", "false", "no"}

    missing = [name for name, value in {
        "SMTP_HOST": host,
        "SMTP_USER": username,
        "SMTP_PASSWORD": password,
        "sender": sender,
        "recipient": recipient,
    }.items() if not value]
    if missing:
        print(f"Email skipped: missing {', '.join(missing)}.")
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls(context=context)
        smtp.login(username, password)
        smtp.send_message(message)
    print(f"Email sent to {recipient}.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Send the weekly Kitaly backup status email.")
    parser.add_argument("--project-dir", default=str(PROJECT_ROOT), help="Kitaly project directory.")
    parser.add_argument("--backup-dir", default=None, help="Directory where backups are stored.")
    parser.add_argument("--log-path", default=None, help="Backup log path.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    env = load_env(project_dir / ".env")
    backup_dir = Path(args.backup_dir or env.get("BACKUP_DIR") or DEFAULT_BACKUP_DIR).resolve()
    log_path = Path(args.log_path or env.get("BACKUP_LOG_PATH") or DEFAULT_LOG_PATH).resolve()
    recipient = env.get("BACKUP_REPORT_EMAIL") or env.get("OFFICIAL_EMAIL")

    status_ok, report = build_report(backup_dir, log_path)
    subject_status = "OK" if status_ok else "ATTENTION"
    subject = f"Kitaly backup weekly status: {subject_status}"
    print(report)
    send_email(env, recipient, subject, report)


if __name__ == "__main__":
    main()
