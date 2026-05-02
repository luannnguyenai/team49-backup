# P2 — Data Pipeline

## Goal

Build the English-only SFT datasets used in ablation runs A/B/C/D.

## Inputs

### Domain anchor

- `question_bank.jsonl`
- `units.jsonl`
- `qa_history.jsonl` if curated and on-scope

### Auxiliary style data

- Filtered ELI5 subset only

## Data pipeline steps

### 1. Audit the domain dataset

Record:

- source names
- sample counts
- language distribution
- domain coverage
- held-out split policy

### 2. Normalize to English

- translate any Vietnamese or mixed-language content to English
- keep technical terms intact
- reject low-quality translations

### 3. Convert to chat format

Use a stable chat template with:

- system prompt for English tutor behavior
- user question
- assistant answer

### 4. Filter ELI5

Apply:

- topic filtering
- answer-length filtering
- noise exclusion
- style quality review

### 5. Prepare ablation mixes

| Run | Mix |
|---|---|
| A | domain only |
| B | domain + 10% ELI5 |
| C | domain + 20% ELI5 |
| D | domain + 30% ELI5 |

### 6. Split eval sets

- internal held-out domain set
- filtered ELI5 dev/test
- external benchmark manifests

## Output artifacts

- `data/sft/run_a_train.jsonl`
- `data/sft/run_b_train.jsonl`
- `data/sft/run_c_train.jsonl`
- `data/sft/run_d_train.jsonl`
- `data/sft/val.jsonl`
- `data/sft/test.jsonl`
- `eval/domain_eval.jsonl`
- `eval/eli5_style_eval.jsonl`
