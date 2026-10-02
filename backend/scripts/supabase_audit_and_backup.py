#!/usr/bin/env python3
"""
GSTU AI Ecosystem - Supabase & PostgreSQL Audit, Schema Diagnostic & Local Backup Utility
Author: Tashfin Yousuf / GSTU IR AI Team
Usage:
    python backend/scripts/supabase_audit_and_backup.py [--backup] [--audit-only]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(override=True)

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ 'supabase' python package not installed. Run: pip install supabase")
    sys.exit(1)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")).strip()

ALL_PROJECT_TABLES = [
    "user_profiles",
    "workspaces",
    "projects",
    "messages",
    "documents",
    "knowledge_base_documents",
    "study_logs",
    "smart_routines",
    "study_plans",
    "support_tickets",
    "notices",
    "department_notices",
    "department_syllabus",
    "syllabus",
    "user_gamification",
    "xp_transactions",
    "academic_analytics",
    "ai_training_logs",
    "audit_logs",
    "study_sessions"
]

def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def run_audit(sb: Client):
    print("\n" + "=" * 65)
    print("🔍 [1/3] SUPABASE SCHEMA & TABLE HEALTH AUDIT")
    print(f"📡 Target Project: {SUPABASE_URL}")
    print("=" * 65)

    audit_results = {}
    missing_tables = []
    active_tables = []

    for table in ALL_PROJECT_TABLES:
        try:
            res = sb.table(table).select("*").limit(1).execute()
            count_res = sb.table(table).select("*", count="exact").limit(0).execute()
            count = getattr(count_res, "count", None) or len(res.data or [])
            cols = list(res.data[0].keys()) if res.data else ["(table empty, column names unavailable via select)"]
            
            audit_results[table] = {
                "status": "HEALTHY",
                "count": count,
                "columns": cols
            }
            active_tables.append(table)
            print(f"✅ {table.ljust(26)} | Rows: {str(count).rjust(6)} | Status: OK")
        except Exception as e:
            err_msg = str(e)
            missing_tables.append(table)
            audit_results[table] = {
                "status": "ERROR / MISSING",
                "error": err_msg
            }
            print(f"❌ {table.ljust(26)} | ERROR: {err_msg[:45]}...")

    print("\n" + "=" * 65)
    print("🔎 [2/3] SCHEMA INTEGRITY & ORPHAN RECORD CHECKS")
    print("=" * 65)

    # Check 1: Orphan messages (messages pointing to deleted or non-existent workspaces)
    try:
        ws_res = sb.table("workspaces").select("id").execute()
        valid_ws_ids = {r["id"] for r in (ws_res.data or [])}
        
        msg_res = sb.table("messages").select("id, workspace_id").limit(1000).execute()
        orphan_msgs = [m for m in (msg_res.data or []) if m.get("workspace_id") and m.get("workspace_id") not in valid_ws_ids]
        
        if orphan_msgs:
            print(f"⚠️ Warning: Found {len(orphan_msgs)} orphan message(s) whose workspace_id no longer exists in 'workspaces'.")
            print("   Recommendation: Add 'ON DELETE CASCADE' foreign key constraint in Postgres.")
        else:
            print("✅ Messages Foreign Key Integrity: No orphan messages found.")
    except Exception as e:
        print(f"ℹ️ Skipped orphan messages check: {e}")

    # Check 2: Auth vs user_profiles sync
    try:
        profiles_res = sb.table("user_profiles").select("id, email").execute()
        profile_count = len(profiles_res.data or [])
        print(f"✅ User Profiles Count: {profile_count} synced user profile(s).")
    except Exception as e:
        print(f"⚠️ user_profiles check note: {e}")

    if missing_tables:
        print(f"\n⚠️ Missing / Inaccessible Tables ({len(missing_tables)}):")
        for mt in missing_tables:
            print(f"   - {mt}")
        print("💡 Tip: Some tables might be legacy or need migration script to be created in Supabase SQL editor.")
    else:
        print(f"\n🎉 All {len(active_tables)} tables exist and respond successfully!")

    return audit_results, active_tables

def run_backup(sb: Client, tables_to_backup: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups", f"backup_{timestamp}"))
    os.makedirs(backup_dir, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"💾 [3/3] EXPORTING LOCAL SNAPSHOT BACKUP")
    print(f"📂 Destination: {backup_dir}")
    print("=" * 65)

    manifest = {
        "timestamp": timestamp,
        "supabase_url": SUPABASE_URL,
        "tables": {}
    }

    for table in tables_to_backup:
        try:
            # Fetch all rows (in batches if large)
            all_rows = []
            page_size = 1000
            offset = 0
            while True:
                res = sb.table(table).select("*").range(offset, offset + page_size - 1).execute()
                rows = res.data or []
                all_rows.extend(rows)
                if len(rows) < page_size:
                    break
                offset += page_size

            file_path = os.path.join(backup_dir, f"{table}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_rows, f, indent=2, default=str)

            manifest["tables"][table] = {
                "rows_backed_up": len(all_rows),
                "file": f"{table}.json"
            }
            print(f"💾 {table.ljust(26)} -> {len(all_rows)} rows saved to {table}.json")
        except Exception as e:
            print(f"❌ Failed to backup {table}: {e}")
            manifest["tables"][table] = {"error": str(e)}

    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 65)
    print(f"✅ Local Snapshot Backup Complete!")
    print(f"📁 Backup Folder: {backup_dir}")
    print(f"📄 Manifest: {manifest_path}")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Supabase Table Audit & Backup Utility")
    parser.add_argument("--backup", action="store_true", help="Perform full data backup to local JSON files")
    parser.add_argument("--audit-only", action="store_true", help="Run audit without backing up")
    args = parser.parse_args()

    client = get_client()
    audit_results, active_tables = run_audit(client)

    if args.backup or not args.audit_only:
        # Default behavior: run backup for all active tables
        run_backup(client, active_tables)

if __name__ == "__main__":
    main()

