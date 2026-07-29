# Same catalogue, two API shapes, one agent

A small experiment: take one messy-but-realistic vehicle parts catalogue,
expose it through two API designs, and run the same scripted agent
against both.

- **v1** — designed the way most catalogue/e-commerce APIs are designed
  today: prose documentation, undefined behaviour when a required field
  is omitted, no idempotency on writes, supersession handled silently.
- **v2** — same data, same operations, designed with an agent as the
  primary consumer: valid values returned in-band, structured errors
  that name the next action, idempotency keys on writes, supersession
  surfaced with a confidence score instead of hidden.

## Results (100 generated repair requests, one run)

| Metric                       | v1 (human-shaped) | v2 (agent-shaped) |
|-------------------------------|:---:|:---:|
| Wrong part ordered            | 8   | 0   |
| Silently ordered obsolete part| 1   | 0   |
| Duplicate orders (timeout retry) | 13  | 0   |
| Escalated to human instead of guessing | 0 | 20 |
| Avg tool calls / request      | 2.13 | 1.91 |

Full row-level detail: [`results/raw_results.csv`](results/raw_results.csv)
Summary: [`results/summary.json`](results/summary.json)

Reproduce it yourself:

```bash
cd src
python3 run_experiment.py
```

## What's actually being measured

The catalogue ([`src/catalogue.py`](src/catalogue.py)) is small and
invented — 4 vehicles, ~62 parts — but it deliberately contains the three
things that make real parts data hard:

1. **Handedness.** Headlamps, fenders, mirrors etc. come in left/right
   pairs. If a request doesn't specify which side, an API can either
   force the caller to say, or silently guess.
2. **Supersession.** A part number gets replaced mid-production by a
   revised one. Asking for the old number by default is easy to do
   without noticing.
3. **Undefined ordering.** When a query matches more than one part and
   no tiebreak rule is specified, "which one comes back" depends on
   implementation details the caller can't see.

The two APIs ([`src/api_v1.py`](src/api_v1.py), [`src/api_v2.py`](src/api_v2.py))
sit on top of the identical data and answer the identical questions —
only the contract differs.

## The agent is scripted, not a live model call — and that's stated on purpose

This was built in a sandbox without internet access, so there's no live
call to an LLM here. [`src/agent.py`](src/agent.py) is a small script
that encodes specific, named failure patterns — guessing at an unstated
required field, not checking for supersession, retrying a timed-out
write with no de-duplication — because those are the concrete behaviours
that show up when an autonomous caller meets an API that wasn't designed
for one.

The value of the exercise isn't "look, AI got it wrong." It's that the
**same naive logic, run against two different API contracts, produces
measurably different failure rates** — and the difference is explainable
mechanically, not just observed. That's the argument, and it holds
whether the caller is a hand-written script or a real model.

If you want to make this more rigorous, the obvious next step is
swapping `agent.py`'s scripted logic for real calls to a model with
tool use, using the same two API clients as its available tools.

## Files

```
src/
  catalogue.py       parts data: vehicles, handedness, supersessions
  api_v1.py           human-shaped API
  api_v2.py           agent-shaped API
  requests_sample.py  generates 100 repair requests with controlled ambiguity
  agent.py            scripted stand-in agent, run against both APIs
  run_experiment.py   runs everything, writes results/
results/
  raw_results.csv     one row per request per API version
  summary.json        aggregated metrics
WRITEUP.md            short write-up / post draft based on these results
```

## Not affiliated with any specific company

This uses an invented catalogue and invented API design, not any real
company's data or documentation.
