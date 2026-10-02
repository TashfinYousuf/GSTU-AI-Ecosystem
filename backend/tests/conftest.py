import sys
import os

# backend ডিরেক্টরিকে sys.path-এর শীর্ষে যুক্ত করা
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)