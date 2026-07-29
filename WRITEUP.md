# What changes when your API's caller is an agent, not a developer

Most catalogue/e-commerce APIs are built for a human who reads the docs
before writing code. Increasingly, the caller is an agent that only ever
sees the runtime responses. I wanted to see, mechanically, what that
difference actually costs — so I built a small experiment.

**Setup:** one invented parts catalogue (4 vehicles, ~62 parts) with the
three things that make real catalogues hard — left/right handed parts,
a mid-production part supersession, and cases where a query has more
than one valid match. I exposed it two ways: a "v1" API shaped like
most catalogue APIs today (prose docs, undefined behaviour on missing
fields, no write idempotency, silent supersession), and a "v2" API
shaped for an agent (valid values returned in-band, structured errors
that name the next action, idempotency keys, supersession surfaced with
a confidence score). Same data, same operations, different contract.

I ran the same simple scripted agent — one that guesses at unstated
values and retries blindly on timeout, because that's the class of
mistake agentic callers actually make — against both, over 100
generated repair requests.

**Results:**

| | v1 (human-shaped) | v2 (agent-shaped) |
|---|:---:|:---:|
| Wrong part ordered | 8% | 0% |
| Silently ordered an obsolete part | 1% | 0% |
| Duplicate orders under retry | 13% | 0% |
| Escalated to a human instead of guessing | 0% | 20% |

The interesting number isn't the 8% wrong-part rate. It's the 20%
escalation rate in v2. The agent-shaped API didn't make the agent
smarter — it made it *stop* in exactly the cases where guessing would
have been wrong, and hand those back to a human instead. That's a
better outcome than a marginally higher hit rate: a wrong part ordered
against a real vehicle is a returned order, a delayed repair, and
sometimes a supplementary claim. A flagged-for-review request is a
five-second human decision.

The duplicate-order number is the one I'd flag hardest to anyone
building transactional APIs right now. Agents retry aggressively and
non-deterministically. Without an idempotency key on every write, a
network hiccup becomes a duplicate order — and the retry logic that
causes it isn't a bug, it's the agent doing exactly what naive retry
logic is supposed to do.

None of this required a live model in the loop to demonstrate — the
same script, unchanged, produces a materially different failure profile
purely because of how the API responds. That's the point: designing
for agentic consumers isn't a prompting problem, it's a schema and
contract problem, and it shows up in the numbers before you ever add a
real model.

Repo with the full code and results: [link]

---

*Built with an invented catalogue, not tied to any specific company's
API or data.*
