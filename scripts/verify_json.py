#!/usr/bin/env python3
"""verify_json.py - JSON 文件健康检查"""
import json, glob, os, sys

data_dir = "/home/admin/openclaw/workspace/stock-assistant/data"
broken = []
for f in glob.glob(f"{data_dir}/*.json"):
    try:
        with open(f) as fp:
            json.load(fp)
    except Exception as e:
        broken.append(f"{os.path.basename(f)}: {e}")

if broken:
    print("BROKEN:" + "|".join(broken))
    sys.exit(1)
else:
    print("all_ok")
    sys.exit(0)
