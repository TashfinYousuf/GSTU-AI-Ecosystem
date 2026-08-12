"""
Run from your backend/ directory:
    python3 audit_supabase_usage.py

Does NOT modify anything. Scans the 19 "no match" files (and anything
else under app/) for any Supabase-client-creation pattern the previous
script's narrow regex might have missed — different spacing, os.environ
instead of os.getenv, a different variable name, multi-line calls, etc.
Prints the actual line(s) found so you can judge each one by eye.
"""
import os
import re

TARGET_DIRS = ["app/api", "app/services", "app/core"]

# Broad patterns — anything that smells like Supabase client setup
SUSPECT_PATTERNS = [
    re.compile(r'create_client\s*\('),
    re.compile(r'SUPABASE_(KEY|ANON_KEY|SERVICE_ROLE_KEY)\s*='),
    re.compile(r'os\.(getenv|environ\.get)\(\s*["\']SUPABASE'),
]

for base_dir in TARGET_DIRS:
    if not os.path.isdir(base_dir):
        continue
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            hits = []
            for i, line in enumerate(lines, start=1):
                if any(p.search(line) for p in SUSPECT_PATTERNS):
                    hits.append((i, line.rstrip()))

            if hits:
                has_service_role = any("SERVICE_ROLE" in line for _, line in hits)
                flag = "✅ has fallback" if has_service_role else "⚠️  NO FALLBACK — check this one"
                print(f"\n{fpath}  [{flag}]")
                for lineno, text in hits:
                    print(f"   L{lineno}: {text}")