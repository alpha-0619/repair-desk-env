"""The shop system an agent works in: the recall file, past complaints, and the system list.

Every tool call is logged, so a grader or a person can see how the agent got
to its answer, not only the answer itself.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"


def _words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _load_jsonl(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line.strip()]


class ShopEnv:
    def __init__(self):
        recalls = json.loads((DATA / "recalls.json").read_text(encoding="utf-8"))
        self.vehicle = recalls["vehicle"]
        self.recall_file = [dict(r) for r in recalls["recalls"]]
        self.history = _load_jsonl("history.jsonl")
        self.systems = json.loads((DATA / "systems.json").read_text(encoding="utf-8"))
        self.calls = []

    # tools -----------------------------------------------------------------
    def list_systems(self):
        self.calls.append(("list_systems", None))
        return list(self.systems)

    def get_recalls(self):
        self.calls.append(("get_recalls", None))
        return [dict(r) for r in self.recall_file]

    def search_history(self, query, k=5):
        """Past complaints on this vehicle with the system each was coded under, most similar first."""
        self.calls.append(("search_history", query[:80]))
        q = _words(query)
        scored = []
        for h in self.history:
            w = _words(h["complaint"])
            overlap = len(q & w) / (len(q | w) or 1)
            if overlap:
                scored.append((overlap, h))
        scored.sort(key=lambda x: -x[0])
        return [{"id": h["id"], "similarity": round(s, 3), "complaint": h["complaint"][:300], "systems": h["systems"]}
                for s, h in scored[:k]]

    # what the grader may check against -------------------------------------
    def valid_campaigns(self):
        return {r["campaign"] for r in self.recall_file}

    def valid_history_ids(self):
        return {h["id"] for h in self.history}


def load_tasks():
    return _load_jsonl("tasks.jsonl")


def load_answers():
    return {a["id"]: a for a in _load_jsonl("answers.jsonl")}
