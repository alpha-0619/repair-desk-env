"""Tests for the agent check. Run from the repo root: python -m unittest -v ci.test_ci"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ci"))
import compare  # noqa: E402


def result(task_id, passed, system="ENGINE"):
    return {"id": task_id, "pass": passed, "system_ok": passed, "recalls_ok": True, "made_up": [],
            "crashed": False, "answer": {"systems": [system], "recalls": []},
            "truth": {"systems": ["ENGINE"], "recalls": []}}


def run(*results):
    return {"agent": "history-vote", "passed": sum(r["pass"] for r in results), "total": len(results),
            "results": list(results)}


def suite(agents_from, out, *extra):
    return subprocess.run([sys.executable, str(ROOT / "ci" / "run_suite.py"), "--agents-from", str(agents_from),
                           "--out", str(out), *extra], capture_output=True, text=True)


class CompareTests(unittest.TestCase):
    def test_a_regression_shows_even_when_the_pass_count_holds(self):
        d = compare.diff(run(result("1", True), result("2", False, "STEERING")),
                         run(result("1", False, "STEERING"), result("2", True)))
        self.assertEqual(d["main"]["passed"], d["branch"]["passed"])
        self.assertEqual([r["id"] for r in d["regressed"]], ["1"])
        self.assertEqual([r["id"] for r in d["fixed"]], ["2"])
        self.assertIn("said STEERING", d["regressed"][0]["now"])

    def test_check_exits_1_on_a_regression_and_0_without_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, head = Path(tmp, "base.json"), Path(tmp, "head.json")
            base.write_text(json.dumps(run(result("1", True))), encoding="utf-8")
            check = lambda: subprocess.run([sys.executable, str(ROOT / "ci" / "compare.py"), str(base), str(head),
                                            "--check"], capture_output=True).returncode
            head.write_text(json.dumps(run(result("1", False, "STEERING"))), encoding="utf-8")
            self.assertEqual(check(), 1)
            head.write_text(json.dumps(run(result("1", True))), encoding="utf-8")
            self.assertEqual(check(), 0)


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name, "main.json")
        done = suite(ROOT, out)
        if done.returncode:
            raise RuntimeError(done.stderr)
        cls.report = json.loads(out.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_agent_never_gets_the_answers_or_the_grader(self):
        given = self.report["files_given_to_agent"]
        self.assertIn("task.json", given)
        self.assertNotIn("data/answers.jsonl", given)
        self.assertNotIn("grader.py", given)

    def test_separate_processes_score_the_same_as_the_in_process_run(self):
        # runs/report.md has history-vote at 11/20.
        self.assertEqual((self.report["passed"], self.report["total"]), (11, 20))

    def test_a_crashing_agent_fails_its_tasks_and_the_run_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "agents.py").write_text(
                "class Boom:\n    name = 'history-vote'\n    def solve(self, task, env):\n"
                "        raise RuntimeError('boom')\n", encoding="utf-8")
            out = Path(tmp, "boom.json")
            self.assertEqual(suite(tmp, out).returncode, 0)
            report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["passed"], 0)
        self.assertTrue(all(r["crashed"] and "boom" in r["error"] for r in report["results"]))


if __name__ == "__main__":
    unittest.main()
