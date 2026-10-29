"""Runs inside one task's folder: builds the shop tools from the files next to it,
asks the named agent for an answer, and writes out.json. The answers are not here."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # python -I leaves the script's folder off sys.path

import agents  # noqa: E402  the agent code under test
from env import ShopEnv  # noqa: E402


def pick(name):
    for obj in vars(agents).values():
        if isinstance(obj, type) and getattr(obj, "name", None) == name:
            return obj()
    raise SystemExit(f"no agent named {name!r} in agents.py")


def main():
    agent = pick(sys.argv[1])
    task = json.loads((HERE / "task.json").read_text(encoding="utf-8"))
    env = ShopEnv()
    answer = agent.solve(task, env)
    (HERE / "out.json").write_text(json.dumps({"answer": answer, "tool_calls": env.calls}), encoding="utf-8")


if __name__ == "__main__":
    main()
