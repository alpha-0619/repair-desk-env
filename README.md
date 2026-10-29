# repair-desk-env

A small agent environment built from real public records: owner complaints and recalls for the 2018 Honda Accord, published by the U.S. National Highway Traffic Safety Administration (NHTSA).

The agent works a service desk. It reads one owner's complaint, can look up the recall file and past complaints on the same vehicle, and has to say which system failed and which open recalls, if any, cover it. The grader checks the answer against the real record.

## What's in it

- `fetch_data.py`: a snapshot of NHTSA's public complaints and recalls APIs (1,897 complaints and 6 recalls, fetched 2026-10-28).
- `build_tasks.py`: 20 tasks (10 where a recall covers the system NHTSA coded, 10 where none does), the hidden answers, a history the agent can search, and the recall file the tools serve.
- `env.py`: the sandbox. Tools: `list_systems`, `get_recalls`, `search_history`. Every call is logged.
- `grader.py`: a task passes only with the right first system (NHTSA's coding), the exact recall list (a missed recall and an extra one both fail), and nothing made up (a campaign or record id that doesn't exist fails the task).
- `agents.py`: three baselines, `always-engine`, `history-vote` and `makes-up-recalls`.
- `test_grader.py`: 12 tests, grader cases plus leakage checks. Breaking the grader on purpose makes them fail.
- `ci/` and `.github/workflows/agent-check.yml`: a check that runs on every pull request. See "Checking an agent change" below.

## Results

From `runs/report.md`:

| agent | system right | recall list right | made something up | passed |
|---|---|---|---|---|
| always-engine | 1/20 | 10/20 | 0/20 | 1/20 |
| history-vote | 11/20 | 13/20 | 0/20 | 11/20 |
| makes-up-recalls | 11/20 | 0/20 | 20/20 | 0/20 |

`always-engine` gets half the recall lists right just by always answering "none". That's why a pass needs every check at once.

## Leaks the first run caught

- 59 complaints repeat word for word under different record numbers, so a task could also sit in the history the agent searches. Repeats are dropped, and history entries that overlap a task by 80% or more of their words are removed.
- 470 complaints name a recall or campaign number in the text, which puts the answer in the question. They never become tasks.

## Checking an agent change

A pass rate on its own hides what moved. When someone changes the agent and opens a pull request, the check:

1. runs the agent from main and the agent from the branch on all 20 tasks;
2. gives each task a fresh container with no network and a read-only filesystem, holding only the task, the tools and the agent code, never the answers file;
3. grades both runs outside the containers, with the tasks, answers and grader from main, so changing the agent doesn't change what it is scored against;
4. comments the pass rate against main, which tasks regressed and which got fixed, and attaches the per-task diff as JSON;
5. fails if any task that passed on main fails on the branch, even when the total goes up.

The workflow pins every action and the container image to an exact version.

Example: widening `history-vote`'s search from 7 to 12 past complaints takes it from 11/20 to 10/20. The check shows more than the one-point drop: 2 tasks regressed, 1 got fixed, and 7 of 20 answers changed.

`ci/test_ci.py` covers the comparison, the `--check` exit code, that the agent's folder holds neither the answers nor the grader, that separate processes score the same 11/20 as the in-process run, and that a crashing agent fails its tasks without stopping the run. It also runs an agent that skips the complaint and reads the answers file by its full path: 20/20 as a plain process, 0/20 in a container.

## Limits

- The outcome here is NHTSA's component coding plus the recall file, matched at system level (for example `FUEL SYSTEM, GASOLINE`). A repair order with the technician's finding, and whether the car came back, would be a stronger label.
- 20 tasks on one vehicle: enough to show the grader separates good, lazy and made-up answers, not enough to rank models.
- `search_history` is word overlap. A real environment would expose the tools a shop actually uses.
- Run locally without `--sandbox docker`, the check uses plain processes. That keeps honest agents apart but doesn't stop one that goes looking, as the test above shows. CI always uses containers.
- The workflow file lives in the repository, so a pull request can edit the check itself. A hosted service would keep the tasks, answers and grader outside the team's repository.
- Each task runs once, which is enough for these deterministic agents. An LLM agent answers differently from run to run, so its check needs several runs per task and should only flag a regression bigger than that spread.
- The agents are scripted baselines. No LLM agent has been run against these tasks yet.

## Run it

Python standard library only.

```
python fetch_data.py
python build_tasks.py
python -m unittest -v test_grader
python run_eval.py
```

The agent check, locally:

```
python ci/run_suite.py --agents-from . --sandbox docker --out runs/ci/main.json
python ci/run_suite.py --agents-from path/to/other/checkout --sandbox docker --out runs/ci/branch.json
python ci/compare.py runs/ci/main.json runs/ci/branch.json
python -m unittest -v ci.test_ci
```
