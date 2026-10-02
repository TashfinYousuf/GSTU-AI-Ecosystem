#!/usr/bin/env bash
set -e

echo "🔍 Running GSTU AI Static Security Audit..."
echo "--------------------------------------------------"

echo "1. Costly / AI-heavy endpoints missing Rate Limiter (@limiter)..."
grep -rnE "@router\.(post|get)" backend/app/api/*.py | grep -vE "(limiter|auth|health|__pycache__)" || true

echo -e "\n2. Scanning for potential Token / Secret / PII leaks in print statements..."
# শুধুমাত্র print(...) এর ভেতরে token, key, secret ইত্যাদি থাকলে ধরবে
grep -rnE "print\s*\(.*(token|secret|password|jwt|current_user)" backend/app/ --exclude-dir=__pycache__ || true

echo -e "\n3. Checking for bare except clauses (Swallowed Exceptions)..."
grep -rnE "except\s*:" backend/app/ --exclude-dir=__pycache__ || true

echo -e "\n4. Scanning for endpoints missing Authentication Dependencies..."
python3 -c '
import ast, glob

for file in glob.glob("backend/app/api/*.py"):
    with open(file, "r") as f:
        try:
            tree = ast.parse(f.read(), filename=file)
        except Exception:
            continue
        for node in ast.walk(tree):
            # def এবং async def উভয়েই চেক করবে
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_route = any(
                    isinstance(d, ast.Call) and getattr(d.func, "attr", "") in ["get", "post", "put", "delete", "patch"]
                    for d in node.decorator_list
                )
                if has_route:
                    # পাবলিক বা হেলথ চেক এন্ডপয়েন্ট বাইপাস
                    if node.name in ["health_check", "root", "login", "sync_user_with_db", "get_daily_toast"]:
                        continue
                    
                    # পুরো আর্গুমেন্ট সিগনেচার আনপার্স করে ডিপেন্ডেন্সি চেক
                    args_str = ast.unparse(node.args)
                    has_auth = "Depends" in args_str and any(
                        k in args_str for k in ["current_user", "faculty", "admin", "security", "require_"]
                    )
                    if not has_auth:
                        print(f"⚠️  UNPROTECTED ROUTE: {file} -> {node.name}()")
'

echo "--------------------------------------------------"
echo "✅ Static scan completed."