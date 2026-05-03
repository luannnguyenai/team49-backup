# Datasets for Fine-tuning

This catalog is aligned to the English-only tutor plan. The project dataset is the primary source of domain knowledge. External data is used only when it fills a clearly defined gap.

## Priority tiers

| Tier | Purpose | Train on it? |
|---|---|---|
| Tier 0 | Eval-only benchmarks | No |
| Tier 1 | Project domain dataset | Yes |
| Tier 2 | Filtered ELI5 explanation-style corpus | Yes |
| Tier 3 | Optional format-balancing data | Maybe, capped |

## Tier 0 — Eval only

Do not train on these.

| Dataset | Use |
|---|---|
| Held-out internal domain set | Main shipping gate |
| `cais/mmlu` selected subjects | Academic regression check |
| `TIGER-Lab/MMLU-Pro` | Harder reasoning regression check |
| `TIGER-Lab/TheoremQA` | Technical reasoning check |
| Filtered ELI5 dev/test | Explanation-style eval only |

Recommended MMLU subjects:

- `machine_learning`
- `college_computer_science`
- `college_mathematics`
- `high_school_statistics`
- optional: `formal_logic`

## Tier 1 — Project domain dataset

This remains the domain anchor and should dominate the training mix.

Suggested sources:

- `question_bank.jsonl`
- `units.jsonl`
- `qa_history.jsonl` after quality review

Expected uses:

- concept explanation
- comparison questions
- applied reasoning tied to course material

## Tier 2 — Filtered ELI5

Use only as an auxiliary explanation corpus.

### Intended benefit

- longer English answers
- better explanatory flow
- more natural why/how responses

### Not intended to provide

- primary AI/ML knowledge
- course-grounded facts
- benchmark supervision

### Filtering rules

| Group | Rule |
|---|---|
| Question type | prefer `why`, `how`, `difference`, `what happens`, `how does` |
| Topic | science, math, computing, probability, optimization, ML, NLP, CV |
| Answer length | roughly 120-450 words |
| Exclude | politics, sports, celebrity, joke-heavy, anecdotal, low-coherence |

### Mixing cap

- 10% for first auxiliary run
- 20% for likely main candidate
- 30% only as a drift stress test

## Tier 3 — Optional format-balancing data

Use only if evaluation shows a concrete gap not solved by the project dataset plus ELI5.

Examples:

- small English instruction-format data for template consistency
- small English tutor-style data for response structure

Rules:

- keep total Tier 3 usage at 5-10%
- do not let it replace project data or filtered ELI5 logic
- do not add generic chat corpora without a documented need

## Recommended v1 mixing recipe

| Source | Share |
|---|---|
| Project domain dataset | 65-75% |
| Filtered ELI5 | 20-30% |
| Optional format-balancing data | 5-10% |

## Hard exclusions from the previous plan

These are out of scope for the current training strategy:

- Vietnamese instruction datasets
- Vietnamese evaluation targets
- vision-language retention corpora
- tool-calling preservation corpora
- multimodal OCR or VQA datasets

Those may return in a future plan only if the product target changes again.
