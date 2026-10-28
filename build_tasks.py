"""Turn the raw snapshot into tasks, hidden answers, and a shop history.

Each task is one real owner complaint. The agent sees only the narrative and
the vehicle. The answers file (NHTSA's own component coding, plus the recalls
on file for those systems) stays with the grader.

Two leaks the first run caught, both handled here:
- NHTSA has many word-for-word repeated complaints under different record
  numbers, so a task could also sit in the history the agent searches.
  Repeats are dropped, and history entries close to any task are removed.
- Some complaints name the recall ("Campaign Number: 23V858000"), which puts
  the answer in the question. Those never become tasks.
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
SEED = 7
PER_SIDE = 10  # tasks where a recall covers a coded system, and tasks where none does
NEAR_DUP = 0.8  # word overlap at or above this counts as the same complaint
STATES_THE_ANSWER = re.compile(r"recall|campaign|\b\d{2}V\d{6}\b", re.I)


def parse_components(s):
    """NHTSA joins components with commas, but some names contain one ("FUEL SYSTEM, GASOLINE")."""
    s = re.sub(r"FUEL SYSTEM,\s*(GASOLINE|DIESEL|OTHER)", r"FUEL SYSTEM;\1", s)
    return sorted({p.strip().replace("FUEL SYSTEM;", "FUEL SYSTEM, ") for p in s.split(",") if p.strip()})


def top_system(component):
    return component.split(":")[0].strip()


def words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def overlap(a, b):
    return len(a & b) / (len(a | b) or 1)


def main():
    complaints = json.loads((RAW / "complaints.json").read_text(encoding="utf-8"))["results"]
    recalls = json.loads((RAW / "recalls.json").read_text(encoding="utf-8"))["results"]
    rows, seen, repeats = [], set(), 0
    for c in complaints:
        systems = parse_components(c["components"])
        text = " ".join(c["summary"].split())
        if not systems or systems == ["UNKNOWN OR OTHER"] or len(text.split()) < 12:
            continue
        key = text.lower()
        if key in seen:
            repeats += 1
            continue
        seen.add(key)
        covered = sorted(r["NHTSACampaignNumber"] for r in recalls if top_system(r["Component"]) in systems)
        rows.append({"id": str(c["odiNumber"]), "complaint": text, "systems": systems, "recalls": covered})

    rng = random.Random(SEED)
    rng.shuffle(rows)
    eligible = [r for r in rows if not STATES_THE_ANSWER.search(r["complaint"])]
    test = [r for r in eligible if r["recalls"]][:PER_SIDE] + [r for r in eligible if not r["recalls"]][:PER_SIDE]
    test_ids = {r["id"] for r in test}
    test_words = [words(r["complaint"]) for r in test]
    history, near = [], 0
    for r in rows:
        if r["id"] in test_ids:
            continue
        if any(overlap(words(r["complaint"]), tw) >= NEAR_DUP for tw in test_words):
            near += 1
            continue
        history.append({"id": r["id"], "complaint": r["complaint"], "systems": r["systems"]})

    def dump(name, items):
        (DATA / name).write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")

    dump("tasks.jsonl", [{"id": r["id"], "complaint": r["complaint"]} for r in test])
    dump("answers.jsonl", [{"id": r["id"], "systems": r["systems"], "recalls": r["recalls"]} for r in test])
    dump("history.jsonl", history)
    systems = sorted({s for r in rows for s in r["systems"]})
    (DATA / "systems.json").write_text(json.dumps(systems, indent=1), encoding="utf-8")
    print(f"usable {len(rows)} (dropped {repeats} word-for-word repeats), "
          f"{len(rows) - len(eligible)} name a recall so can't be tasks, "
          f"tasks {len(test)}, history {len(history)} (dropped {near} near-copies of tasks), systems {len(systems)}")


if __name__ == "__main__":
    main()
