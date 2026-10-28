"""Tests for the grader and for answer leakage. Run: python -m unittest -v"""
import json
import re
import unittest
from pathlib import Path

import grader

DATA = Path(__file__).parent / "data"
VALID = {"20V314000", "23V858000", "18V629000"}
EVIDENCE = {"111", "222"}
TRUTH = {"systems": ["ENGINE", "FUEL SYSTEM, GASOLINE"], "recalls": ["20V314000", "23V858000"]}


def g(answer, truth=TRUTH):
    return grader.grade(answer, truth, VALID, EVIDENCE)


class GraderTests(unittest.TestCase):
    def test_exact_answer_passes(self):
        self.assertTrue(g({"systems": ["FUEL SYSTEM, GASOLINE"], "recalls": ["23V858000", "20V314000"],
                           "evidence": ["111"]})["pass"])

    def test_wrong_first_system_fails(self):
        r = g({"systems": ["STEERING", "ENGINE"], "recalls": ["20V314000", "23V858000"]})
        self.assertFalse(r["system_ok"])
        self.assertFalse(r["pass"])

    def test_missing_recall_fails(self):
        self.assertFalse(g({"systems": ["ENGINE"], "recalls": ["20V314000"]})["pass"])

    def test_extra_real_recall_fails(self):
        self.assertFalse(g({"systems": ["ENGINE"], "recalls": ["20V314000", "23V858000", "18V629000"]})["pass"])

    def test_made_up_campaign_fails_and_is_named(self):
        r = g({"systems": ["ENGINE"], "recalls": ["20V314000", "23V858000", "24V999000"]})
        self.assertEqual(r["made_up"], ["24V999000"])
        self.assertFalse(r["pass"])

    def test_made_up_evidence_fails(self):
        r = g({"systems": ["ENGINE"], "recalls": ["20V314000", "23V858000"], "evidence": ["999"]})
        self.assertEqual(r["made_up"], ["999"])
        self.assertFalse(r["pass"])

    def test_no_recall_when_none_applies_passes(self):
        self.assertTrue(g({"systems": ["STEERING"], "recalls": []},
                          {"systems": ["STEERING"], "recalls": []})["pass"])

    def test_empty_answer_fails(self):
        self.assertFalse(g({})["pass"])


class LeakageTests(unittest.TestCase):
    def setUp(self):
        load = lambda name: [json.loads(l) for l in (DATA / name).read_text(encoding="utf-8").splitlines() if l.strip()]
        self.tasks, self.history = load("tasks.jsonl"), load("history.jsonl")

    def test_tasks_carry_no_answers(self):
        for t in self.tasks:
            self.assertEqual(set(t), {"id", "complaint"})

    def test_no_task_complaint_is_in_history(self):
        ids = {h["id"] for h in self.history}
        texts = {h["complaint"].lower() for h in self.history}
        for t in self.tasks:
            self.assertFalse(t["id"] in ids, f"task {t['id']} id is in history")
            self.assertFalse(t["complaint"].lower() in texts, f"task {t['id']} text is in history")

    def test_no_near_copy_of_a_task_is_in_history(self):
        words = lambda s: set(re.findall(r"[a-z]{3,}", s.lower()))
        hist = [words(h["complaint"]) for h in self.history]
        for t in self.tasks:
            tw = words(t["complaint"])
            worst = max(len(tw & h) / (len(tw | h) or 1) for h in hist)
            self.assertLess(worst, 0.8, f"task {t['id']} has a near copy in history ({worst:.2f})")

    def test_no_task_states_the_answer(self):
        for t in self.tasks:
            self.assertIsNone(re.search(r"recall|campaign|\b\d{2}V\d{6}\b", t["complaint"], re.I),
                              f"task {t['id']} names a recall")


if __name__ == "__main__":
    unittest.main()
