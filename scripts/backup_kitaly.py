#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_DIR = Path("/var/backups/kitaly")
DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_BACKUP_BYTES = 3 * 1024 ** 3
DEFAULT_MIN_FREE_BYTES = 2 * 1024 ** 3


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


def parse_mysql_url(database_url):
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("mysql"):
        raise ValueError("Only MySQL DATABASE_URL values are supported for production backups.")

    return {
        "host": parsed.host or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "database": parsed.database,
    }


def run_mysqldump(database, destination):
    mysqldump = shutil.which("mysqldump")
    if not mysqldump:
        raise RuntimeError("mysqldump was not found on this server.")

    env = os.environ.copy()
    env["MYSQL_PWD"] = database["password"]
    command = [
        mysqldump,
        "--single-transaction",
        "--quick",
        "--routines",
        "--triggers",
        "--events",
        "--no-tablespaces",
        "-h",
        database["host"],
        "-P",
        str(database["port"]),
        "-u",
        database["user"],
        database["database"],
    ]
    with destination.open("wb") as output:
        subprocess.run(command, env=env, stdout=output, stderr=subprocess.PIPE, check=True)


def add_directory_to_tar(archive, source, arcname):
    if not source.exists():
        return
    archive.add(source, arcname=arcname, recursive=True)


def prune_old_backups(backup_dir, retention_days, max_bytes=DEFAULT_MAX_BACKUP_BYTES):
    cutoff_seconds = retention_days * 24 * 60 * 60
    now = datetime.now(timezone.utc).timestamp()
    removed = []
    backups = sorted(backup_dir.glob("kitaly_backup_*.tar.gz"), key=lambda p: p.stat().st_mtime)
    total_bytes = sum(path.stat().st_size for path in backups)
    # Always retain the newest completed backup, even if it exceeds the budget.
    for path in backups[:-1]:
        age_seconds = now - path.stat().st_mtime
        if age_seconds > cutoff_seconds or total_bytes > max_bytes:
            total_bytes -= path.stat().st_size
            path.unlink()
            removed.append(path.name)
    return removed


def main():
    parser = argparse.ArgumentParser(description="Create a full Kitaly backup with database and product images.")
    parser.add_argument("--project-dir", default=str(PROJECT_ROOT), help="Kitaly project directory.")
    parser.add_argument("--backup-dir", default=None, help="Directory where backups are stored.")
    parser.add_argument("--retention-days", type=int, default=None, help="Days to keep backup archives.")
    parser.add_argument("--max-backup-bytes", type=int, default=None, help="Maximum completed backup storage.")
    parser.add_argument("--min-free-bytes", type=int, default=None, help="Disk space reserved for the live site.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    env = load_env(project_dir / ".env")
    database_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is missing.")

    upload_folder = env.get("UPLOAD_FOLDER") or os.environ.get("UPLOAD_FOLDER") or "uploads"
    upload_path = Path(upload_folder)
    if not upload_path.is_absolute():
        upload_path = project_dir / upload_path

    backup_dir = Path(args.backup_dir or env.get("BACKUP_DIR") or DEFAULT_BACKUP_DIR).resolve()
    retention_days = args.retention_days or int(env.get("BACKUP_RETENTION_DAYS") or DEFAULT_RETENTION_DAYS)
    max_bytes = args.max_backup_bytes if args.max_backup_bytes is not None else int(env.get("BACKUP_MAX_BYTES") or DEFAULT_MAX_BACKUP_BYTES)
    min_free_bytes = args.min_free_bytes if args.min_free_bytes is not None else int(env.get("BACKUP_MIN_FREE_BYTES") or DEFAULT_MIN_FREE_BYTES)
    if retention_days <= 0 or max_bytes <= 0 or min_free_bytes <= 0:
        raise SystemExit("Backup retention and storage limits must be positive.")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Do not delete recovery points before a replacement has completed. If the
    # disk is already tight, stop rather than taking down uploads and MySQL.
    upload_files = [path for path in upload_path.rglob("*") if path.is_file()] if upload_path.exists() else []
    estimated_bytes = sum(path.stat().st_size for path in upload_files) + 64 * 1024 ** 2
    if shutil.disk_usage(backup_dir).free < min_free_bytes + estimated_bytes:
        raise SystemExit("Insufficient disk space for backup while preserving the live-site reserve.")

    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%d_%H%M%S")
    final_archive = backup_dir / f"kitaly_backup_{stamp}.tar.gz"
    temp_archive = backup_dir / f".{final_archive.name}.tmp"

    database = parse_mysql_url(database_url)
    with tempfile.TemporaryDirectory(prefix="kitaly_backup_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        database_dump = temp_dir / "database.sql"
        manifest_path = temp_dir / "manifest.json"
        run_mysqldump(database, database_dump)

        manifest = {
            "created_at_utc": created_at.isoformat(),
            "project_dir": str(project_dir),
            "database": database["database"],
            "upload_folder": str(upload_path),
            "upload_file_count": len(upload_files),
            "retention_days": retention_days,
            "max_backup_bytes": max_bytes,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        try:
            with tarfile.open(temp_archive, "w:gz") as archive:
                archive.add(database_dump, arcname="database.sql")
                archive.add(manifest_path, arcname="manifest.json")
                add_directory_to_tar(archive, upload_path, "uploads")
        except BaseException:
            temp_archive.unlink(missing_ok=True)
            raise

    os.replace(temp_archive, final_archive)
    final_archive.chmod(0o600)
    removed = prune_old_backups(backup_dir, retention_days, max_bytes)

    size_mb = final_archive.stat().st_size / (1024 * 1024)
    print(
        f"OK created {final_archive} ({size_mb:.2f} MB), "
        f"uploads={manifest['upload_file_count']}, pruned={len(removed)}"
    )
    for name in removed:
        print(f"pruned {name}")


if __name__ == "__main__":
    main()
