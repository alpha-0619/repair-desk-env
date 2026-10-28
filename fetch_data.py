"""Fetch a snapshot of public NHTSA complaints and recalls for one vehicle.

Source: the U.S. National Highway Traffic Safety Administration's public APIs
(api.nhtsa.gov). Complaint narratives are published by NHTSA. The snapshot is
kept as fetched; build_tasks.py drops VINs and dates before anything reaches
an agent.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VEHICLE = {"make": "honda", "model": "accord", "modelYear": "2018"}
OUT = Path(__file__).parent / "data" / "raw"


def get(path):
    url = f"https://api.nhtsa.gov/{path}?{urllib.parse.urlencode(VEHICLE)}"
    req = urllib.request.Request(url, headers={"User-Agent": "repair-desk-env (research demo)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    for name, path in [("complaints", "complaints/complaintsByVehicle"),
                       ("recalls", "recalls/recallsByVehicle")]:
        data = get(path)
        data["_fetched_at"] = stamp
        data["_vehicle"] = VEHICLE
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, len(data.get("results", [])), "records, fetched", stamp)


if __name__ == "__main__":
    main()
