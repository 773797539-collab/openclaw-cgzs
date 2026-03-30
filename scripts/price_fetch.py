#!/usr/bin/env python3
"""独立价格获取脚本，避免 akshare import 超时"""
import sys, json, urllib.request, urllib.error

def fetch_price(code):
    # 1. 试 MCP HTTP
    for ip in ["82.156.17.205", "82.156.17.206"]:
        try:
            req = urllib.request.Request(
                f"http://{ip}:8000/price?code={code}",
                headers={"Content-Type": "application/json"},
                timeout=2
            )
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
                if isinstance(data, dict) and "price" in data:
                    return data
        except:
            pass

    # 2. 试东方财富 API
    try:
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid=1.{code}&fields=f43,f169,f170,f171"
        req = urllib.request.Request(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            f43 = data.get("data", {}).get("f43")
            if f43:
                price = float(f43) / 100
                return {"price": price, "source": "eastmoney"}
    except:
        pass

    return None

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "605365"
    result = fetch_price(code)
    if result:
        print(json.dumps(result))
    else:
        print(json.dumps({"error": "price unavailable"}))
