#!/usr/bin/env python3
"""Build data.json from the Google Sheet CSV for the audience pulse dashboard."""
import csv
import io
import json
import sys
import urllib.request

CSV_URL = "https://docs.google.com/spreadsheets/d/1hXojkDNaNL0t8KtP5K1zcAAsA4kHUJHylfMCB0zdA8w/export?format=csv"

def fetch_csv():
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8-sig")

def parse(raw):
    reader = csv.reader(io.StringIO(raw))
    header = next(reader)
    rows = []
    for r in reader:
        if len(r) < 7 or not r[3].strip():
            continue
        try:
            rows.append({
                "role": r[1].strip(),
                "size": r[2].strip(),
                "p3": int(r[3].strip()),
                "p4": int(r[4].strip()),
                "p5": int(r[5].strip()),
                "p6": int(r[6].strip()),
            })
        except (ValueError, IndexError):
            continue
    return rows

def compute(data):
    n = len(data)
    if n == 0:
        return {"n": 0}

    avg = lambda arr: sum(arr) / len(arr) if arr else 0
    median = lambda arr: (lambda s: s[len(s)//2] if len(s) % 2 else (s[len(s)//2-1]+s[len(s)//2])/2)(sorted(arr))

    p3 = [d["p3"] for d in data]
    p4 = [d["p4"] for d in data]
    p5 = [d["p5"] for d in data]
    p6 = [d["p6"] for d in data]

    avgP3, avgP4, avgP5, avgP6 = avg(p3), avg(p4), avg(p5), avg(p6)
    meanSensing = avg([avgP3, avgP4, avgP5])
    meanVelocity = avgP6
    gap = meanSensing - meanVelocity

    def dist(arr):
        d = {i: 0 for i in range(1, 8)}
        for v in arr:
            d[v] = d.get(v, 0) + 1
        return d

    def count_by(key):
        c = {}
        for d in data:
            c[d[key]] = c.get(d[key], 0) + 1
        return c

    def gap_by(key):
        groups = {}
        for d in data:
            groups.setdefault(d[key], []).append(d)
        result = {}
        for k, v in groups.items():
            s = avg([(d["p3"] + d["p4"] + d["p5"]) / 3 for d in v])
            vel = avg([d["p6"] for d in v])
            result[k] = {"sensing": round(s, 2), "velocity": round(vel, 2), "gap": round(s - vel, 2), "n": len(v)}
        return result

    scatter = [{"x": round((d["p3"] + d["p4"] + d["p5"]) / 3, 2), "y": d["p6"]} for d in data]
    quads = {"Leaders": 0, "Stuck at Sensing": 0, "Reactive": 0, "Laggards": 0}
    for p in scatter:
        if p["x"] >= 4.5 and p["y"] >= 4.5:
            quads["Leaders"] += 1
        elif p["x"] >= 4.5 and p["y"] < 4.5:
            quads["Stuck at Sensing"] += 1
        elif p["x"] < 4.5 and p["y"] >= 4.5:
            quads["Reactive"] += 1
        else:
            quads["Laggards"] += 1

    return {
        "n": n,
        "meanSensing": round(meanSensing, 2),
        "meanVelocity": round(meanVelocity, 2),
        "gap": round(gap, 2),
        "avgP3": round(avgP3, 2), "avgP4": round(avgP4, 2),
        "avgP5": round(avgP5, 2), "avgP6": round(avgP6, 2),
        "medP3": median(p3), "medP4": median(p4),
        "medP5": median(p5), "medP6": median(p6),
        "distP3": dist(p3), "distP4": dist(p4),
        "distP5": dist(p5), "distP6": dist(p6),
        "roles": count_by("role"),
        "sizes": count_by("size"),
        "gapBySize": gap_by("size"),
        "gapByRole": gap_by("role"),
        "scatter": scatter,
        "quadrants": quads,
    }

if __name__ == "__main__":
    raw = fetch_csv()
    data = parse(raw)
    stats = compute(data)
    out_path = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {out_path} with {stats['n']} responses")
    print(f"  Mean Sensing: {stats.get('meanSensing','N/A')}")
    print(f"  Mean Velocity: {stats.get('meanVelocity','N/A')}")
    print(f"  Gap: {stats.get('gap','N/A')}")
    print(f"  Quadrants: {stats.get('quadrants','N/A')}")
