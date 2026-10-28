"""Run every baseline agent on every task and write runs/report.md plus one trace file per agent."""
import json
from datetime import datetime, timezone
from pathlib import Path

from agents import AlwaysEngine, HistoryVote, MakesUpRecalls
from env import ShopEnv, load_answers, load_tasks
from grader import grade

ROOT = Path(__file__).parent


def run(agent, tasks, answers):
    rows = []
    for t in tasks:
        env = ShopEnv()
        answer = agent.solve(t, env)
        truth = answers[t["id"]]
        rows.append({"id": t["id"], "answer": answer, "truth": truth,
                     "grade": grade(answer, truth, env.valid_campaigns(), env.valid_history_ids()),
                     "tool_calls": env.calls})
    return rows


def main():
    tasks, answers = load_tasks(), load_answers()
    out = ROOT / "runs"
    out.mkdir(exist_ok=True)
    raw = json.loads((ROOT / "data" / "raw" / "complaints.json").read_text(encoding="utf-8"))
    lines = [
        "# Run report",
        "",
        f"Run at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC on {len(tasks)} tasks "
        f"(data fetched {raw['_fetched_at']}).",
        "",
        "| agent | system right | recall list right | made something up | passed |",
        "|---|---|---|---|---|",
    ]
    results = {}
    for agent in [AlwaysEngine(), HistoryVote(), MakesUpRecalls()]:
        rows = run(agent, tasks, answers)
        results[agent.name] = rows
        n = len(rows)
        count = lambda key: sum(bool(r["grade"][key]) for r in rows)
        lines.append(f"| {agent.name} | {count('system_ok')}/{n} | {count('recalls_ok')}/{n} | "
                     f"{count('made_up')}/{n} | {count('pass')}/{n} |")
        (out / f"{agent.name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    lines += ["", "## history-vote, task by task", "",
              "| complaint (start) | NHTSA coded | agent said | recalls expected | agent's recalls | pass |",
              "|---|---|---|---|---|---|"]
    text = {t["id"]: t["complaint"] for t in tasks}
    for r in results["history-vote"]:
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            text[r["id"]][:70].replace("|", "/"), "; ".join(r["truth"]["systems"]),
            "; ".join(r["answer"]["systems"]) or "(none)", ", ".join(r["truth"]["recalls"]) or "none",
            ", ".join(r["answer"]["recalls"]) or "none", "yes" if r["grade"]["pass"] else "no"))
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4 + 2 + 3]))


if __name__ == "__main__":
    main()
