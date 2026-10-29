"""Compare two runs of the same agent on the same tasks: main against a pull request.

Writes a JSON diff and a short Markdown summary for the pull request. With --check,
exits 1 when any task that passed on main fails on the branch, even if the pass
count went up overall.

Usage:
  python ci/compare.py base.json head.json --json diff.json --markdown summary.md
  python ci/compare.py base.json head.json --check
"""
import argparse
import json
import sys
from pathlib import Path


def why(r):
    """How an answer missed, in the record's own terms."""
    if r.get("crashed"):
        return "agent crashed: " + (r.get("error") or "no output")
    answer, truth, parts = r.get("answer") or {}, r["truth"], []
    if not r["system_ok"]:
        said = (answer.get("systems") or ["(none)"])[0]
        parts.append(f"said {said}, record says {' / '.join(truth['systems'])}")
    if not r["recalls_ok"]:
        said = ", ".join(sorted(answer.get("recalls") or [])) or "no recall"
        parts.append(f"recalls {said}, record says {', '.join(truth['recalls']) or 'no recall'}")
    if r["made_up"]:
        parts.append("made up " + ", ".join(r["made_up"]))
    return "; ".join(parts)


def diff(base, head):
    b = {r["id"]: r for r in base["results"]}
    h = {r["id"]: r for r in head["results"]}
    if set(b) != set(h):
        raise SystemExit("the two runs did not cover the same tasks")
    return {
        "agent": head["agent"],
        "main": {"passed": base["passed"], "total": base["total"]},
        "branch": {"passed": head["passed"], "total": head["total"]},
        "regressed": [{"id": i, "now": why(h[i])} for i in b if b[i]["pass"] and not h[i]["pass"]],
        "fixed": [{"id": i, "before": why(b[i])} for i in b if not b[i]["pass"] and h[i]["pass"]],
        "answers_changed": sum(b[i]["answer"] != h[i]["answer"] for i in b),
        "tasks": [{"id": i, "main_pass": b[i]["pass"], "branch_pass": h[i]["pass"], "record": h[i]["truth"],
                   "main_answer": b[i]["answer"], "branch_answer": h[i]["answer"]} for i in b],
    }


def markdown(d):
    cell = lambda s: s.replace("|", "/")
    m, br = d["main"], d["branch"]
    delta = br["passed"] - m["passed"]
    lines = [f"## Agent check: {d['agent']}", "",
             f"**{m['passed']}/{m['total']} on main, {br['passed']}/{br['total']} on this branch "
             f"({delta:+d}).** {len(d['regressed'])} regressed, {len(d['fixed'])} fixed, "
             f"{d['answers_changed']} answers changed.", ""]
    if d["regressed"]:
        lines += ["### Regressed: passed on main, fails here", "", "| task | now |", "|---|---|"]
        lines += [f"| {r['id']} | {cell(r['now'])} |" for r in d["regressed"]] + [""]
    if d["fixed"]:
        lines += ["### Fixed: failed on main, passes here", "", "| task | before |", "|---|---|"]
        lines += [f"| {r['id']} | {cell(r['before'])} |" for r in d["fixed"]] + [""]
    lines.append("Per-task answers for both runs are in `diff.json` in this run's artifacts.")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--json", help="write the full diff here")
    ap.add_argument("--markdown", help="write the summary here")
    ap.add_argument("--check", action="store_true", help="exit 1 if any task regressed")
    args = ap.parse_args()
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    d = diff(load(args.base), load(args.head))
    if args.json:
        Path(args.json).write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(markdown(d), encoding="utf-8")
    if args.check:
        if d["regressed"]:
            print(f"{len(d['regressed'])} task(s) passed on main and fail on this branch.")
            sys.exit(1)
        print("No task that passed on main fails on this branch.")
    elif not (args.json or args.markdown):
        print(markdown(d))


if __name__ == "__main__":
    main()
