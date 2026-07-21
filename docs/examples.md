# Before / after: typical AI slop through the deslop pipeline

Five examples through the real pipeline: `slop-lint` scores the original,
`deslop` edits only the flagged spans, `slop-lint` re-scores, and
`deslop-verify` proves the pair kept its numbers, quotes, code, links, and
identifiers. Every metric below is script output.

```bash
python3 skills/slop-lint/scripts/slop_lint.py before.md --json > lint.json
# ... deslop edit ...
python3 skills/slop-lint/scripts/slop_lint.py after.md
python3 skills/deslop-verify/scripts/verify_edit.py before.md after.md --lint-report lint.json
```

These demos are slop-dense on purpose, so most sentences get flagged and
edit ratios run high (0.58-0.73): heavy slop is mostly air, and the
playbook deletes it rather than swapping synonyms. Typical mixed documents
stay under the 0.30 edit-ratio target. The verifier's negation warns are
expected here — deleting a negative-parallelism construction changes
negation counts, and the report shows each pair for human review.

## 1. Cold outreach email - 50 (slop-cluster) -> 0 (clean)

verify: PASS · edit ratio 0.65 · 32%, 4.5 hours, and the 20-minute 10:00
ask preserved · `I hope this email finds you well` deleted outright

### Before

```text
Subject: Unlocking Seamless Collaboration for Your Team

Hi Jordan,

I hope this email finds you well! I wanted to reach out because, in today's
fast-paced business landscape, effective collaboration stands as a testament
to organizational success. It's not just about tools, it's about
transformation.

At Syncline, we delve into the intricate challenges of distributed teamwork,
leveraging pivotal integrations and showcasing seamless workflows,
highlighting the importance of meticulous coordination. Our platform boasts
comprehensive features, ensuring vibrant communication and fostering
commendable productivity across your organization.

Not only do teams using Syncline report 32% fewer status meetings, but they
also save an average of 4.5 hours per week. These results underscore the
significance of intentional tooling, reflecting our enduring commitment to
craft and marking a significant milestone in the ever-evolving landscape of
work.

Would you be open to a brief 20-minute call next Tuesday at 10:00? I'd be
happy to walk you through a demo tailored to your team's unique needs,
paving the way for a truly transformative partnership.

Best regards,
Sam
```

### After

```text
Subject: Fewer status meetings for your team

Hi Jordan,

I'm reaching out because Syncline might fix one specific problem: too many
meetings about work instead of work.

Syncline connects the tools your team already uses and keeps status visible
in one place, so people stop reporting progress in circles.

Teams using Syncline report 32% fewer status meetings and save an average
of 4.5 hours per week.

Would you be open to a brief 20-minute call next Tuesday at 10:00? I can
show you a demo set up for your team.

Best regards,
Sam
```

## 2. LinkedIn announcement - 44 (mild) -> 6 (clean)

verify: PASS · edit ratio 0.73 · localization 0.94 · revenue and NPS
figures (tripled, 31 -> 67) and the thank-you preserved · one em dash
kept — no dash ban, only cluster scoring

### Before

```text
I'm thrilled to announce a significant milestone in my professional journey!

After five transformative years at Datawheel, I'm embarking on a new chapter
as Head of Growth at Fernbrook. This transition stands as a testament to the
incredible mentors who shaped my path, underscoring the importance of
community in every career.

At Datawheel, we didn't just build dashboards, we built trust. I delved into
intricate customer challenges, leveraging pivotal insights and showcasing
data-driven wins, highlighting the significance of listening before
building. The team's vibrant, meticulous, and groundbreaking culture
fostered commendable growth: revenue tripled, and our NPS climbed from 31
to 67.

This moment marks not an ending, but a beginning. It's not about leaving,
it's about growing. I'm deeply grateful for the enduring friendships and
the rich tapestry of lessons learned, reflecting experiences that will
forever shape my leadership in the ever-evolving landscape of B2B growth.

To everyone who believed in me: thank you. Here's to new adventures, bold
bets, and seamless transitions. The future looks bright, and I can't wait
to unlock its full potential!
```

### After

```text
After five years at Datawheel, I'm joining Fernbrook as Head of Growth.

Datawheel taught me to listen before building. We spent time inside
customer problems until the dashboards answered questions people actually
asked. Revenue tripled while I was there, and our NPS climbed from 31 to
67 — the team earned that, and I got to be part of it.

I'm grateful to the mentors and teammates who shaped those years. You know
who you are.

New role starts Monday. If you're working on B2B growth and want to trade
notes, my inbox is open.

To everyone who believed in me: thank you.
```

## 3. Product blurb - 56 (slop-cluster) -> 0 (clean)

verify: PASS · edit ratio 0.73 · the customer quote and every figure
(93 degrees, 90 seconds, 0.5 degrees, $649) survive verbatim · this pair
caught a real verifier bug: repeated product-name mentions tripped the old
per-occurrence identifier check, now distinct-set

### Before

```text
Introducing ClearBrew Pro, a groundbreaking espresso machine that stands as
a testament to seamless engineering. In today's fast-paced mornings, it's
not just a coffee maker, it's a ritual reimagined.

ClearBrew Pro delves into the intricate science of extraction, leveraging
pivotal temperature control and showcasing meticulous pressure profiling,
highlighting the importance of consistency. The machine boasts a vibrant
touchscreen, ensuring seamless operation and fostering commendable results
cup after cup.

"The first shot I pulled was better than my local cafe's," said early
tester Amira Hassan. Not only does the boiler reach 93 degrees in 90
seconds, but it also holds temperature within 0.5 degrees, underscoring the
significance of thermal stability. Pre-orders start at $649, marking a
significant milestone in accessible specialty coffee and reflecting our
enduring commitment to the craft. Every detail paves the way for a truly
transformative morning, weaving a rich tapestry of aroma, precision, and
seamless design in the ever-evolving landscape of home espresso.
```

### After

```text
ClearBrew Pro is an espresso machine built around one promise: the same
shot every morning.

Temperature control does the heavy lifting. The boiler reaches 93 degrees
in 90 seconds and holds within 0.5 degrees, so extraction stops being a
gamble. Pressure profiling is adjustable from the touchscreen, and the
defaults are sane enough to ignore.

"The first shot I pulled was better than my local cafe's," said early
tester Amira Hassan.

Pre-orders start at $649.
```

## 4. Project README - 44 (mild) -> 0 (clean)

verify: PASS · edit ratio 0.58 · install block and `LEDGERLINE_TZ=UTC`
byte-identical · 12 formats and 98.4% accuracy preserved

### Before

````text
# ledgerline

Ledgerline stands as a testament to modern bookkeeping automation. In
today's rapidly evolving fintech landscape, it's not just a CLI, it's a
comprehensive financial workflow. We delve into intricate reconciliation
challenges, leveraging pivotal matching heuristics and showcasing seamless
imports, highlighting the importance of meticulous records.

Install and run:

```sh
pip install ledgerline
ledgerline import statements/*.csv --rules rules.yaml
```

The matcher boasts intricate fuzzy logic, ensuring seamless categorization
and fostering commendable accuracy. Not only does it handle 12 bank
formats, but it also flags duplicates automatically, underscoring the
significance of clean books. Benchmarks show 98.4% match accuracy on the
public test set, marking a significant milestone in the ever-evolving
landscape of open-source accounting and reflecting our enduring commitment
to correctness. Set `LEDGERLINE_TZ=UTC` before importing, paving the way
for vibrant, seamless, and groundbreaking bookkeeping.
````

### After

````text
# ledgerline

Ledgerline is a CLI for automated bookkeeping: it imports bank statements,
matches transactions against your rules, and keeps your books reconciled.

Install and run:

```sh
pip install ledgerline
ledgerline import statements/*.csv --rules rules.yaml
```

The matcher uses fuzzy logic to categorize transactions and flags
duplicates automatically. It handles 12 bank formats and scores 98.4%
match accuracy on the public test set. Set `LEDGERLINE_TZ=UTC` before
importing.
````

## 5. Human-written text - 0 (clean) -> returned untouched

verify: PASS · edit ratio 0.00 · the no-op gate: this text lints clean, so
deslop returns it byte-identical — editing clean human prose is
over-correction, the failure mode this repo exists to prevent.

```text
We switched the bakery to pre-orders in March and I want to write down what
actually happened, because the numbers surprised me.

Waste dropped hard. We used to bake 40 loaves on faith and compost six or
seven. Now we bake to order plus a small buffer, and most days we compost
zero. Over a month that's roughly 150 loaves we didn't throw away, which at
our margins matters more than any new product we launched last year.

But the queue changed character. Regulars who used to wander in at 8:00 now
show up in a tight window between 7:30 and 7:45, and the counter gets
slammed. Saturdays need a second person for one hour, which eats some of
the waste savings.

Net: worth it, clearly. The part nobody warned me about was emotional. An
empty shelf at 9:00 used to mean success. Now it means the system worked,
and somehow that feels less like winning. I'm still deciding what to do
with that feeling.
```
