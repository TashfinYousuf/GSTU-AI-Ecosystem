#!/usr/bin/env python3
"""
Run this from your backend/ directory:
    python3 fix_supabase_keys.py

What it does:
- Scans every .py file under app/api/, app/services/, app/core/
- Finds the exact pattern: SUPABASE_KEY = os.getenv("SUPABASE_KEY")
  (with or without surrounding whitespace)
- Replaces ONLY that line with the fallback version, leaving everything
  else in each file completely untouched.
- Skips files that already have the fallback (SUPABASE_SERVICE_ROLE_KEY)
  so it's safe to run multiple times.
- Prints exactly which files it changed, and which it skipped.

This is a narrow, line-level find-replace — it does NOT restructure your
files, does NOT touch any other logic, and does NOT create a shared
client module. It just fixes the crash in every file that has it.
"""
import os
import re

TARGET_DIRS = ["app/api", "app/services", "app/core"]
OLD_PATTERN = re.compile(r'^(\s*)SUPABASE_KEY\s*=\s*os\.getenv\("SUPABASE_KEY"\)\s*$', re.MULTILINE)
NEW_LINE_TEMPLATE = '{indent}SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")'

changed_files = []
skipped_already_fixed = []
skipped_no_match = []

for base_dir in TARGET_DIRS:
    if not os.path.isdir(base_dir):
        continue
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            if "SUPABASE_SERVICE_ROLE_KEY" in content:
                skipped_already_fixed.append(fpath)
                continue

            match = OLD_PATTERN.search(content)
            if not match:
                skipped_no_match.append(fpath)
                continue

            indent = match.group(1)
            new_content = OLD_PATTERN.sub(NEW_LINE_TEMPLATE.format(indent=indent), content, count=1)

            with open(fpath, "w", encoding="utf-8") as f:
                f.write(new_content)

            changed_files.append(fpath)

print(f"\n✅ PATCHED ({len(changed_files)} files):")
for f in changed_files:
    print(f"   - {f}")

print(f"\n⏭️  ALREADY FIXED, skipped ({len(skipped_already_fixed)} files):")
for f in skipped_already_fixed:
    print(f"   - {f}")

print(f"\n⚪ NO MATCH, not touched ({len(skipped_no_match)} files) — these either")
print("   don't use Supabase directly, or use a different variable name")
print("   (e.g. SUPABASE_KEY read with a default value, or SUPABASE_ANON_KEY).")
print("   Check these manually if you still see crashes after this run:")
for f in skipped_no_match:
    print(f"   - {f}")