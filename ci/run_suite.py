"""Run one agent on every task, each in its own folder and its own process, then grade it.

The harness (shop tools, tasks, hidden answers, grader) comes from --harness. Only the
agent code, agents.py, comes from --agents-from. A pull request can change the agent,
but not the tasks, the answers or the grader it is scored by.

Each task folder gets the task, the tool data, the shop tools and the agent code. The
answers file never goes in, and grading happens out here after the agent process exits.
This is process-level separation, not a security sandbox: a hosted version would run
each task in a container with no network.

Usage:
  python ci/run_suite.py --agents-from . --out runs/ci/local.json
  python base/ci/run_suite.py --harness base --agents-from head --out head.json
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_DATA = ["history.jsonl", "systems.json", "recalls.json"]


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_task(task, agent, harness, agents_from, timeout):
    with tempfile.TemporaryDirectory(prefix=f"task-{task['id']}-") as tmp:
        box = Path(tmp)
        (box / "data").mkdir()
        for name in TOOL_DATA:
            shutil.copy(harness / "data" / name, box / "data" / name)
        shutil.copy(harness / "env.py", box / "env.py")
        shutil.copy(HERE / "agent_runner.py", box / "agent_runner.py")
        shutil.copy(agents_from / "agents.py", box / "agents.py")
        (box / "task.json").write_text(json.dumps(task), encoding="utf-8")
        given = sorted(p.relative_to(box).as_posix() for p in box.rglob("*") if p.is_file())
        start = time.monotonic()
        try:
            proc = subprocess.run([sys.executable, "-I", "agent_runner.py", agent], cwd=box,
                                  capture_output=True, text=True, timeout=timeout)
            crashed = proc.returncode != 0 or not (box / "out.json").exists()
            lines = proc.stderr.strip().splitlines()
            error = lines[-1] if crashed and lines else ""
        except subprocess.TimeoutExpired:
            crashed, error = True, f"timed out after {timeout:g}s"
        seconds = round(time.monotonic() - start, 2)
        out = {} if crashed else json.loads((box / "out.json").read_text(encoding="utf-8"))
    return out, crashed, error, seconds, given


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harness", default=str(HERE.parent), help="checkout with the tasks, answers and grader")
    ap.add_argument("--agents-from", required=True, help="checkout whose agents.py is under test")
    ap.add_argument("--agent", help="agent name; defaults to the harness's ci/config.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=60, help="seconds per task")
    args = ap.parse_args()

    harness, agents_from = Path(args.harness).resolve(), Path(args.agents_from).resolve()
    agent = args.agent or json.loads((harness / "ci" / "config.json").read_text(encoding="utf-8"))["agent"]
    sys.path.insert(0, str(harness))
    from grader import grade  # the harness's grader, never the branch's

    tasks = load_jsonl(harness / "data" / "tasks.jsonl")
    answers = {a["id"]: a for a in load_jsonl(harness / "data" / "answers.jsonl")}
    recalls = json.loads((harness / "data" / "recalls.json").read_text(encoding="utf-8"))["recalls"]
    valid_campaigns = {r["campaign"] for r in recalls}
    valid_history = {h["id"] for h in load_jsonl(harness / "data" / "history.jsonl")}

    results, given_files = [], None
    for task in tasks:
        out, crashed, error, seconds, given = run_task(task, agent, harness, agents_from, args.timeout)
        given_files = given_files or given
        answer, truth = out.get("answer") or {}, answers[task["id"]]
        if crashed:
            graded = {"system_ok": False, "recalls_ok": False, "made_up": [], "pass": False}
        else:
            graded = grade(answer, truth, valid_campaigns, valid_history)
        results.append({"id": task["id"], **graded, "crashed": crashed, "error": error, "seconds": seconds,
                        "answer": answer, "truth": truth, "tool_calls": out.get("tool_calls", [])})

    report = {"agent": agent, "agents_from": agents_from.name, "passed": sum(r["pass"] for r in results),
              "total": len(results), "files_given_to_agent": given_files, "results": results}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{agent} ({agents_from.name}): {report['passed']}/{report['total']} passed")


if __name__ == "__main__":
    main()
