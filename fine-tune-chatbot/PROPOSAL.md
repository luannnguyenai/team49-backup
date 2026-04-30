# Proposal: English Fine-tuning Plan for `fine-tune-chatbot`

## 1. Objective

This proposal recommends an updated fine-tuning strategy for the chatbot in this repository with the following decisions:

- Keep the current project dataset unchanged and treat it as the **primary domain dataset**.
- Move the assistant to **full English**.
- Use **`Qwen/Qwen2.5-7B-Instruct`** as the base model.
- Use **ELI5** as a **filtered auxiliary dataset**, not as the sole or dominant training source.
- Benchmark on a stack that is closer to the real task: **AI/ML/NLP/CV tutoring and explanation**, not only generic instruction following.

The key claim of this proposal is:

> ELI5 is useful for training long-form explanatory behavior in English, but it should not replace the project’s existing domain dataset. For this project, ELI5 is best used as a carefully filtered style-and-explanation supplement.

---

## 2. Why the previous direction is weak

From the current `fine-tune-chatbot` folder, the earlier pipeline mainly justifies external data as additional instruction data. That is not strong enough for this project, because the target chatbot is not a generic assistant. It is closer to a **domain tutor** for AI/ML/NLP/CV.

The main risks in the old direction are:

- The external data is too generic relative to the target domain.
- The training objective is not clearly separated into:
  - domain knowledge,
  - explanation style,
  - benchmark behavior.
- The benchmark plan is too broad and not sufficiently aligned with AI/ML/NLP/CV tutoring.

For a convincing plan, we need a tighter argument for:

1. what the project dataset teaches,
2. what ELI5 adds that the project dataset does not,
3. what should never be expected from ELI5,
4. how success will be measured on the actual tutoring task.

---

## 3. Recommended Base Model

Use **`Qwen/Qwen2.5-7B-Instruct`**.

Why this model fits:

- It is a strong open 7B instruction model with good reported performance in **reasoning, coding, structured output, and long-context generation**.
- The current Hugging Face model card lists **Apache-2.0** and support for **128K context** with multilingual ability, including English and Vietnamese.
- For this proposal, English is the main target, so `Qwen2.5-7B-Instruct` is a better fit than a multilingual data mix centered on Vietnamese.

This proposal assumes **text-only fine-tuning**. If the project later needs image-grounded tutoring for CV diagrams or slides, that should be treated as a separate multimodal phase, not mixed into this training decision.

---

## 4. Position on ELI5

## Decision

Use ELI5, but **do not use it raw**, **do not use all of it**, and **do not use it as the main corpus**.

## Why ELI5 is attractive

ELI5 was introduced by Fan et al. as a long-form question answering dataset with about **270K Reddit threads** built around explanatory answers. For this project, that matters because your chatbot needs to do more than output short answers. It needs to:

- answer “why” and “how” questions,
- produce paragraph-length explanations,
- keep an educational tone,
- explain technical ideas more naturally in English.

Those are exactly the parts where ELI5 is stronger than a small domain MCQ dataset.

## Why ELI5 is not enough by itself

ELI5 is still the wrong dataset if used carelessly:

- It is **general-domain**, not AI/ML/NLP/CV-specific.
- It comes from **Reddit**, so style and factual quality are uneven.
- It was built for **long-form QA**, not for course-grounded tutoring.
- Later work showed important issues with the benchmark itself, including **train/validation overlap** and weak automatic metrics for LFQA.

Therefore, ELI5 should be used to teach:

- explanation length,
- answer organization,
- “explain-like-a-teacher” behavior,
- English long-form QA fluency.

It should **not** be treated as the main source of domain truth for AI/ML/NLP/CV.

---

## 5. Why ELI5 still makes sense for this project

ELI5 is worth using here for four concrete reasons.

### 5.1 It complements the current dataset instead of competing with it

Your current dataset already contains the domain signal that matters most to the project. ELI5 contributes a different capability:

- the project dataset teaches **what to say** in your domain,
- ELI5 teaches **how to explain at length in English**.

That division is clean and defensible.

### 5.2 It fits the move to full English

If the project is shifting from mixed-language data to full English, ELI5 is a much better fit than generic translated instruction corpora, because:

- it is naturally English,
- it is explanation-heavy,
- it contains many “why/how” questions rather than only short instruction-response pairs.

### 5.3 It has strong research credibility

ELI5 is not a random Hugging Face clone. It is tied to well-known long-form QA research and later benchmark ecosystems.

It appears in:

- **Fan et al., ACL 2019**: the original ELI5 dataset paper.
- **Petroni et al., NAACL 2021 (KILT)**: ELI5 was included in the KILT benchmark for knowledge-intensive tasks.
- **Krishna et al., NAACL 2021**: a critical paper showing ELI5 is important but must be evaluated carefully.
- **Su et al., Findings of ACL 2022**: used ELI5 as a core LFQA benchmark in faithful long-form QA.
- **WebGPT (OpenAI, 2021)**: trained and evaluated on ELI5-style open-ended questions.

This is exactly the kind of citation trail that makes a dataset choice easier to defend in front of a lecturer.

### 5.4 It supports the right behavioral target

For a tutoring chatbot, many failures are not simple factual errors. They are failures of explanation:

- too short,
- too shallow,
- too list-like,
- not pedagogical,
- not coherent across a paragraph.

ELI5 directly targets that failure mode.

---

## 6. Important caveat: use filtered ELI5, not full ELI5

My recommendation is to create an **ELI5-filtered subset** for this repository.

### 6.1 Filtering rules

Keep only samples that satisfy most of the following:

- Question is explanatory: starts with or strongly implies `why`, `how`, `what happens`, `what is the difference`, `how does`.
- Answer length is moderate-to-long: for example `120-450` words.
- Answer is coherent and expository, not joke-heavy or conversational noise.
- Topic is at least adjacent to science, math, computing, logic, data, perception, language, optimization, probability, or engineering.
- Remove celebrity trivia, sports trivia, politics, entertainment, and other unrelated categories.

### 6.2 Project-specific topic filter

Build a domain relevance filter around keywords and semantic similarity for:

- machine learning
- deep learning
- neural networks
- statistics
- probability
- optimization
- linear algebra
- NLP / language models / embeddings / transformers
- computer vision / CNN / image features / segmentation / detection
- algorithms / computation / information theory

### 6.3 Data quality filter

Drop samples that show:

- obvious opinionated or speculative answers,
- heavy first-person anecdotal style,
- sarcasm or Reddit meta-discussion,
- answer-question mismatch,
- duplicate or near-duplicate prompts.

### 6.4 Final role of ELI5

After filtering, ELI5 should become an **auxiliary corpus for explanation behavior**, not the dominant data source.

---

## 7. Proposed training mix

Recommended first-pass training mix:

- **65-75%**: current project dataset, unchanged
- **20-30%**: filtered ELI5 subset
- **5-10%**: held-back formatting or instruction-balancing data if needed

I do **not** recommend going beyond ~30% ELI5 in v1, because the domain mismatch will start to dominate the model’s behavior.

### Why this ratio is defensible

- The project dataset remains the anchor for AI/ML/NLP/CV knowledge.
- ELI5 adds English explanatory style.
- The model stays domain-focused instead of turning into a generic explainer.

If you later observe weak explanation quality, increase ELI5 modestly.  
If you observe domain drift, reduce ELI5 before changing anything else.

---

## 8. Representative ELI5 data preview

Below are short, **abridged** previews showing the style of data ELI5 contains.

### Example A

- Question: why chemical weapons are considered more indiscriminate than conventional weapons
- Answer style: a multi-sentence explanation discussing spread, persistence, and collateral damage

### Example B

- Question: in football, why waste the first two plays with a rush up the middle
- Answer style: explanatory coaching rationale, not just a one-line fact

### Example C

- Question type in the KILT mirror: short open-domain prompt plus one or more answers with provenance
- Value for this project: can be transformed into instruction-style QA pairs, but still needs domain filtering

These previews illustrate the main benefit:

- ELI5 teaches **explanation structure**,
- but the raw topic distribution is too broad for direct use.

---

## 9. Papers and benchmark ecosystems connected to ELI5

ELI5 is credible because it has been used or discussed in several important research contexts:

1. **ELI5: Long Form Question Answering**  
   Fan et al., ACL 2019  
   Introduced ELI5 as a large-scale long-form QA dataset.

2. **KILT: a Benchmark for Knowledge Intensive Language Tasks**  
   Petroni et al., NAACL 2021  
   Included ELI5 in a broader benchmark with grounded provenance.

3. **Hurdles to Progress in Long-form Question Answering**  
   Krishna et al., NAACL 2021  
   Important because it warns that ELI5 should not be evaluated naively.

4. **Read before Generate! Faithful Long Form Question Answering with Machine Reading**  
   Su et al., Findings of ACL 2022  
   Used ELI5 as one of the main LFQA testbeds.

5. **WebGPT: Improving the factual accuracy of language models through web browsing**  
   OpenAI, December 2021  
   Explicitly trained on open-ended questions from ELI5.

This lets you argue both sides honestly:

- ELI5 is widely recognized and useful,
- but serious papers also document its limitations,
- therefore filtering and careful benchmarking are mandatory.

That is a much stronger proposal than simply saying “ELI5 is large, so we should train on it.”

---

## 10. Recommended benchmark stack for this project

The benchmark should match the real task: **AI/ML/NLP/CV tutoring**, not just generic chat.

## Tier A: Primary benchmark for this repo

Use a **held-out split from the current project dataset** as the main shipping gate.

This is the most important benchmark because it measures exactly what the model will do in this project.

Recommended evaluation units:

- MCQ accuracy on held-out course questions
- open-ended explanation quality on transformed held-out questions
- terminology correctness for AI/ML/NLP/CV concepts
- concise-vs-detailed answer control

Recommended split policy:

- group by lecture / topic / source unit
- keep train/val/test disjoint at the topic level
- never let paraphrases of the same question appear across splits

## Tier B: External domain-relevant academic benchmarks

### 10.1 MMLU subject subsets

Use **MMLU**, but not as a single overall score.  
Use only the subjects that align with the target task:

- `machine_learning`
- `college_computer_science`
- `college_mathematics`
- `high_school_statistics`
- `abstract_algebra` or `formal_logic` as optional stress tests

Why:

- It is standard and recognizable.
- It gives your lecturer an academically familiar benchmark.
- Subject slicing makes it more relevant than a global MMLU average.

### 10.2 MMLU-Pro

Use **MMLU-Pro** as a harder secondary benchmark.

Why:

- It was proposed specifically as a more robust and more challenging successor to MMLU.
- It is useful for verifying that the fine-tuned model does not only memorize easy patterns.

### 10.3 TheoremQA

Use **TheoremQA**, especially the **EE&CS, Math, and Physics** portions.

Why it fits:

- It is much closer to technical reasoning than general chat benchmarks.
- It contains theorem-driven questions curated by experts.
- It is appropriate for a tutor expected to explain math-heavy ML foundations.

This is a very good fit for CS224n / CS231n / CS230-adjacent reasoning.

## Tier C: Style benchmark for explanatory answers

Use an **untouched dev/test slice of filtered ELI5** only as a **style-and-explanation benchmark**.

Do **not** use this as the main success criterion.

Use it to measure:

- answer length control,
- coherence,
- explanatory structure,
- educational tone in English.

This tells you whether ELI5 actually improved the behavior you wanted it to improve.

---

## 11. Benchmarks I do not recommend as primary gates

I do not recommend using these as the main story for this project:

- **global MMLU score only**  
  Too broad and too weakly tied to AI/ML/NLP/CV tutoring.

- **GSM8K alone**  
  Useful for arithmetic reasoning, but too narrow for the target chatbot.

- **generic chat benchmarks**  
  They do not tell you whether the model can explain transformers, backpropagation, attention, or CNNs well.

- **raw ELI5 score as the shipping gate**  
  This would overvalue long-form fluency and undervalue domain correctness.

---

## 12. Concrete benchmark protocol

### 12.1 Before fine-tuning

Evaluate base `Qwen/Qwen2.5-7B-Instruct` on:

- internal held-out domain set
- MMLU selected subjects
- MMLU-Pro selected STEM slice or full
- TheoremQA selected categories
- filtered ELI5 dev slice

### 12.2 After fine-tuning

Run the exact same evaluation and compare deltas.

### 12.3 Success criteria

Recommended practical gates:

- Internal domain benchmark: **must improve**
- MMLU selected subjects: **should not regress materially**
- TheoremQA: **small improvement or no major regression**
- Filtered ELI5 explanation benchmark: **clear improvement in explanation quality**

If internal domain quality improves but MMLU-style scores drop slightly, that can still be acceptable.  
If ELI5-style fluency improves but internal AI/ML/NLP/CV correctness drops, the fine-tune should be rejected.

---

## 13. Practical training plan for this repo

### Phase 1

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Method: QLoRA / LoRA
- Language: English only
- Data:
  - current project dataset unchanged
  - filtered ELI5 subset

### Phase 2

Build three validation files:

- `domain_eval.jsonl`
- `eli5_style_eval.jsonl`
- `external_reasoning_eval.jsonl`

### Phase 3

Track ablations:

- run A: project dataset only
- run B: project dataset + 10% ELI5
- run C: project dataset + 20% ELI5
- run D: project dataset + 30% ELI5

This is important. It will let you prove whether ELI5 is actually helping, instead of assuming it is.

---

## 14. Final recommendation

The strongest proposal for this project is:

1. Keep the existing dataset as the main domain source.
2. Switch to `Qwen/Qwen2.5-7B-Instruct`.
3. Move to full English.
4. Use **filtered ELI5** only as an auxiliary explanation-style dataset.
5. Benchmark primarily on:
   - held-out internal AI/ML/NLP/CV data,
   - MMLU selected subjects,
   - MMLU-Pro,
   - TheoremQA,
   - filtered ELI5 dev for style only.

If you present ELI5 this way, the argument is much stronger:

- it is not replacing your domain data,
- it is filling a clear capability gap,
- it is backed by major papers,
- its known weaknesses are acknowledged and controlled,
- and the benchmark is aligned with the actual tutoring task.

That is a defensible fine-tuning plan for immediate use in this repository.

---

## 15. Source notes

These sources were used to shape this proposal:

- ELI5 official repository: https://github.com/facebookresearch/ELI5
- ELI5 dataset explorer: https://facebookresearch.github.io/ELI5/
- ELI5 original paper (ACL 2019): https://aclanthology.org/P19-1346/
- KILT paper (NAACL 2021): https://aclanthology.org/2021.naacl-main.200/
- Hurdles to Progress in Long-form Question Answering (NAACL 2021): https://aclanthology.org/2021.naacl-main.393/
- Read before Generate! (Findings of ACL 2022): https://aclanthology.org/2022.findings-acl.61/
- WebGPT: https://openai.com/research/webgpt
- Qwen2.5-7B-Instruct model card: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- KILT dataset card on Hugging Face: https://huggingface.co/datasets/facebook/kilt_tasks
- MMLU paper: https://openreview.net/forum?id=d7KBjmI3GmQ
- MMLU-Pro paper: https://huggingface.co/papers/2406.01574
- TheoremQA paper: https://aclanthology.org/2023.emnlp-main.489/

Implementation note:

- The current Hugging Face `facebook/kilt_tasks` dataset card lists `mit`.
- The original ELI5 repository also notes that processed Reddit/CommonCrawl data had hosting constraints.
- For this project, document the exact dataset source you download and pin it in the training manifest.
