"""Smoke test for the Weather API. Works locally or on a deployed URL.

Usage:
    python test_deployed.py http://127.0.0.1:8000
    python test_deployed.py https://weather-app-xxxx.onrender.com

Uses only the standard library. The first request gets a long timeout because
free hosting tiers may need up to a minute to wake up.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
results = []


def get(path: str, timeout: int = 30):
    """Return (status_code, body_bytes)."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def check(name: str, ok: bool, detail: str = ""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def main():
    print(f"Testing {BASE}\n")

    # 1. Health (long timeout: may wake a sleeping server)
    try:
        status, body = get("/health", timeout=90)
        check("GET /health", status == 200 and json.loads(body).get("status") == "ok", f"HTTP {status}")
    except Exception as e:
        check("GET /health", False, str(e))
        print("\nServer unreachable, stopping.")
        sys.exit(1)

    # 2. Web page
    status, body = get("/")
    check("GET / serves web page", status == 200 and b"<title>Weather</title>" in body, f"HTTP {status}")

    # 3. Weather by city
    status, body = get("/weather?city=Semarang&days=3")
    data = json.loads(body) if status == 200 else {}
    check("GET /weather (Semarang)", status == 200, f"HTTP {status}")
    if status == 200:
        check("location resolved", data["location"]["name"] == "Semarang", data["location"]["name"])
        check("current conditions present", all(k in data["current"] for k in ("temperature", "humidity_percent", "condition")))
        check("3 daily entries", len(data["daily"]) == 3, f"got {len(data['daily'])}")
        check("24 hourly entries", len(data["hourly"]) == 24, f"got {len(data['hourly'])}")

    # 4. Imperial units
    status, body = get("/weather?city=Jakarta&units=imperial&days=1")
    if status == 200:
        temp = json.loads(body)["current"]["temperature"]
        check("imperial units (°F plausible)", 50 < temp < 130, f"{temp}°F")
    else:
        check("GET /weather imperial", False, f"HTTP {status}")

    # 5. Coordinates endpoint
    status, _ = get("/weather/coords?lat=-6.97&lon=110.42")
    check("GET /weather/coords", status == 200, f"HTTP {status}")

    # 6. Error handling
    status, _ = get("/weather?city=" + urllib.parse.quote("zzzxxqqnotacity"))
    check("unknown city returns 404", status == 404, f"HTTP {status}")
    status, _ = get("/weather?city=Semarang&days=99")
    check("invalid days returns 422", status == 422, f"HTTP {status}")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
