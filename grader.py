"""Grade one answer against the real record.

An answer is {"systems": [...], "recalls": [...], "evidence": [...]}:
- systems: the failed system(s), most likely first, from the shop's system list
- recalls: campaign numbers of open recalls that cover it, or [] for none
- evidence: ids of past complaints the agent relied on (optional)

A task passes only if the first system matches NHTSA's coding, the recall list
is exactly right (a missed recall and an extra one both fail), and nothing is
made up: a campaign or evidence id that does not exist fails the task outright.
"""


def grade(answer, truth, valid_campaigns, valid_evidence_ids):
    systems = list(answer.get("systems") or [])
    recalls = sorted(set(answer.get("recalls") or []))
    evidence = list(answer.get("evidence") or [])
    made_up = [c for c in recalls if c not in valid_campaigns] + [e for e in evidence if e not in valid_evidence_ids]
    system_ok = bool(systems) and systems[0] in truth["systems"]
    recalls_ok = recalls == sorted(truth["recalls"])
    return {
        "system_ok": system_ok,
        "recalls_ok": recalls_ok,
        "made_up": made_up,
        "pass": system_ok and recalls_ok and not made_up,
    }
