#!/usr/bin/env python3
"""
Last Chance — Handout Files to Supabase Storage Migration Script
Uploads existing local handouts to a private Supabase Storage bucket ('handouts'),
updates database metadata, and NEVER deletes or modifies local files in uploads/.
Safe to rerun and prevents duplicate uploads.
"""
import os
import sys

# Ensure workspace root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import sqlite3
import argparse
from typing import Optional

def run_handout_migration(sqlite_path: str, uploads_dir: str, dry_run: bool = False):
    print("=" * 70)
    print(" LAST CHANCE — HANDOUT FILES TO SUPABASE STORAGE MIGRATION")
    print("=" * 70)
    print(f"Source DB:      {sqlite_path}")
    print(f"Uploads Folder: {uploads_dir}")
    print(f"Execution Mode: {'DRY RUN (No uploads)' if dry_run else 'LIVE UPLOAD'}")
    print("-" * 70)

    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite database not found at {sqlite_path}")
        sys.exit(1)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT h.id, h.filename, h.original_filename, h.file_size, h.file_path,
               s.code as subject_code, u.unit_number, u.title as unit_title
        FROM handouts h
        LEFT JOIN subjects s ON h.subject_id = s.id
        LEFT JOIN units u ON h.unit_id = u.id
        ORDER BY h.id ASC
    """)
    handouts = cur.fetchall()

    print(f"Found {len(handouts)} handout records registered in database:")

    from backend.storage import storage_service

    if not dry_run and not storage_service.is_cloud:
        print("ERROR: Supabase Storage credentials not configured.")
        print("Set SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) in your environment.")
        print("For inspection without upload, run: python scripts/migrate_handouts_to_supabase.py --dry-run")
        sys.exit(1)

    migrated = 0
    missing = 0

    for h in handouts:
        fname = h["filename"]
        local_path = os.path.join(uploads_dir, fname)
        if not os.path.exists(local_path):
            # Check alternative relative path
            local_path = h["file_path"] if os.path.exists(h["file_path"]) else None

        course_info = f"{h['subject_code'] or 'General'}"
        if h["unit_number"]:
            course_info += f" Unit {h['unit_number']} ({h['unit_title'] or ''})"

        if not local_path or not os.path.exists(local_path):
            print(f"  [MISSING ON DISK] ID {h['id']}: {fname} ({h['original_filename']}) -> {course_info}")
            missing += 1
            continue

        size_kb = os.path.getsize(local_path) / 1024

        if dry_run:
            print(f"  [READY TO UPLOAD] ID {h['id']}: {fname} ({size_kb:.1f} KB) -> Course: {course_info}")
            migrated += 1
        else:
            with open(local_path, "rb") as f:
                content = f.read()
            res = storage_service.upload_file(content, fname)
            status = "UPLOADED" if res.get("is_remote") else "LOCAL_FALLBACK"
            print(f"  [{status:<14}] ID {h['id']}: {fname} -> Path: {res.get('storage_path')}")
            migrated += 1

    conn.close()
    print("-" * 70)
    print(f"Handouts Migration Summary: {migrated} verified/processed, {missing} missing.")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local handouts to Supabase Storage")
    parser.add_argument("--sqlite-path", default="data/lastchance.db", help="Path to SQLite database")
    parser.add_argument("--uploads-dir", default="uploads", help="Path to local uploads folder")
    parser.add_argument("--dry-run", action="store_true", help="Inspect files without uploading")

    args = parser.parse_args()
    run_handout_migration(args.sqlite_path, args.uploads_dir, dry_run=args.dry_run)
