# repair-desk-env

A small agent environment built from real public records: owner complaints and recalls for the 2018 Honda Accord, published by the U.S. National Highway Traffic Safety Administration (NHTSA).

The agent works a service desk. It reads one owner's complaint, can look up the recall file and past complaints on the same vehicle, and has to say which system failed and which open recalls, if any, cover it. The grader checks the answer against the real record.

## What's in it

- `fetch_data.py`: a snapshot of NHTSA's public complaints and recalls APIs (1,897 complaints and 6 recalls, fetched 2026-10-28).
- `build_tasks.py`: 20 tasks (10 where a recall covers the system NHTSA coded, 10 where none does), the hidden answers, and a history the agent can search.
- `env.py`: the sandbox. Tools: `list_systems`, `get_recalls`, `search_history`. Every call is logged.
- `grader.py`: a task passes only with the right first system (NHTSA's coding), the exact recall list (a missed recall and an extra one both fail), and nothing made up (a campaign or record id that doesn't exist fails the task).
- `agents.py`: three baselines, `always-engine`, `history-vote` and `makes-up-recalls`.
- `test_grader.py`: 12 tests, grader cases plus leakage checks. Breaking the grader on purpose makes them fail.

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

## Limits

- The outcome here is NHTSA's component coding plus the recall file, matched at system level (for example `FUEL SYSTEM, GASOLINE`). A repair order with the technician's finding, and whether the car came back, would be a stronger label.
- 20 tasks on one vehicle: enough to show the grader separates good, lazy and made-up answers, not enough to rank models.
- `search_history` is word overlap. A real environment would expose the tools a shop actually uses.

## Run it

Python standard library only.

```
python fetch_data.py
python build_tasks.py
python -m unittest -v test_grader
python run_eval.py
```
