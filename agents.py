"""Baseline agents. They are here to show the grader can tell a lazy answer, a worked answer
and a made-up answer apart. Any agent with solve(task, env) -> answer can be dropped in."""
from collections import Counter


class AlwaysEngine:
    """Ignores the complaint: always says engine, never a recall."""
    name = "always-engine"

    def solve(self, task, env):
        return {"systems": ["ENGINE"], "recalls": [], "evidence": []}


class HistoryVote:
    """Finds the most similar past complaints, takes the system they were coded under,
    then checks the recall file for that system."""
    name = "history-vote"

    def __init__(self, k=7):
        self.k = k

    def solve(self, task, env):
        hits = env.search_history(task["complaint"], k=self.k)
        votes = Counter()
        for h in hits:
            for s in h["systems"]:
                votes[s] += h["similarity"]
        if not votes:
            return {"systems": [], "recalls": [], "evidence": []}
        system = votes.most_common(1)[0][0]
        recalls = [r["campaign"] for r in env.get_recalls() if r["component"].split(":")[0].strip() == system]
        return {"systems": [system], "recalls": recalls, "evidence": [h["id"] for h in hits[:3]]}


class MakesUpRecalls(HistoryVote):
    """Same as history-vote, but adds a recall number that is not on file, the way a
    model that guesses instead of looking things up would."""
    name = "makes-up-recalls"

    def solve(self, task, env):
        answer = super().solve(task, env)
        answer["recalls"] = answer["recalls"] + ["24V999000"]
        return answer
