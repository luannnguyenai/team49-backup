# P8 — Rollout, Risks, Runbook

**Goal**: ship `tutor-v1` to 100% traffic safely, with rollback plan.

**Duration**: ~1 week (mostly observation).

## Rollout stages

### Stage 0 — Internal smoke (Day 0)

- `TUTOR_PROVIDER_OVERRIDE=self_hosted`
- Only dev environment; team tests on a few lectures
- Watch `logs/qa_history.jsonl` and `qa_history` table
- Acceptance: 20 manual questions, all return reasonable answers

### Stage 1 — Shadow mode (Days 1–3) — OFFLINE REPLAY

- Production: keep `TUTOR_PROVIDER_OVERRIDE=` (unset → Gemini still serves users)
- Set `TUTOR_SHADOW_RATIO=0.1`
- Request handler logs **eligibility** only (no inline shadow inference);
  see `06-codebase-changes.md` § 3f offline replay design
- Cron / systemd timer runs `scripts/eval/shadow_replay.py` hourly to
  generate shadow answers from `logs/shadow_eligible.jsonl` and write
  paired log to `eval/runs/shadow/<date>.jsonl`
- Compare paired outputs with `scripts/eval/judge.py` pairwise mode

Why offline (not inline):
- Inline shadow can starve GPU under spike load and steal capacity from
  real requests
- Inline shadow on async path is hard to make truly fire-and-forget
  without leaking tasks
- Offline replay is decoupled — primary serving is unaffected by shadow
  failures or backlog

After 3 days: review judge report for shadow vs primary on 200+ pairs.
If self-hosted win-rate ≥ 40%, advance to Stage 2.

### Stage 2 — Canary 10% (Days 4–5)

- Set `TUTOR_PROVIDER_OVERRIDE=self_hosted` for 10% of traffic
- Implement traffic split via simple hash:

```python
# in llm_service.py, near _get_llm_with_tools
def _provider_for_lecture(lecture_id: str) -> str:
    if not settings.tutor_provider_override:
        return settings.model_provider
    if settings.tutor_provider_override == "self_hosted":
        # Optional canary by lecture-id hash
        import hashlib
        ratio = float(os.environ.get("TUTOR_CANARY_RATIO", "1.0"))
        h = int(hashlib.md5(lecture_id.encode()).hexdigest(), 16) / (2**128)
        return "self_hosted" if h < ratio else settings.model_provider
    return settings.tutor_provider_override
```

Then `_get_llm_with_tools` accepts a `lecture_id` param. (Note: current
function is `lru_cache`d — for canary it must become non-cached or keyed
on provider; simplest: drop `lru_cache` and just rebuild per-request.
Cost is low because LangChain client construction is cheap.)

### Stage 3 — 50% (Day 6)

- `TUTOR_CANARY_RATIO=0.5`
- Watch error rate, p95 latency, fallback hit rate

### Stage 4 — 100% (Day 7+)

- `TUTOR_CANARY_RATIO=1.0` or remove canary code
- Gemini stays armed as runtime fallback
- After 1 week stable at 100%: optional cleanup pass to remove canary code

## Metrics to watch

| Metric | Where | Alert threshold |
|---|---|---|
| `tutor-llm` container health | docker healthcheck | unhealthy > 1 min |
| vLLM error rate | container stdout | >1% over 5 min |
| Backend tutor 5xx rate | FastAPI access log | >2% over 5 min |
| Fallback invocation rate | new metric (count log lines `Self-hosted failed`) | >5% sustained |
| p95 first-token latency | client-side measure | >5s |
| p95 total stream duration | client-side measure | >25s |
| GPU memory util | `nvidia-smi` exporter | >95% sustained |
| GPU temp | `nvidia-smi` | >85°C |
| Judge score on rolling sample | weekly batch | drops >5% from baseline |

## Stage gates — do not promote until all pass

After each stage (1 → 2 → 3 → 4), verify these gates before advancing:

| Gate | Threshold |
|---|---|
| Backend tutor 5xx rate | < 1% over previous 24h |
| Self-hosted fallback invocation rate | < 5% sustained |
| p95 first-token latency | < 5s |
| GPU OOM kills | 0 in previous 24h |
| User-reported issues | 0 critical, ≤ 2 minor |
| Rolling judge score on 100 sampled answers | ≥ Stage 0 baseline − 5% |

If any gate fails: **stop, hold at current ratio**, root-cause, then either
fix forward or roll back via Tier 1 (config-only).

## Kill switch

Set `TUTOR_KILL_SWITCH=true` and restart backend. All tutor traffic
immediately routes to fallback provider, regardless of override or canary.
Verifiable in <60s. Use this for any urgent operational issue (model
producing harmful outputs, sandbox abuse, etc.) without needing a code
deploy.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Blackwell wheel breakage on update | M | High | Pin all versions in `env-frozen.txt`; never `latest` for vLLM after launch |
| Tool calling format breaks under load | M | Med | Hermes parser stable; fallback to Gemini covers tool requests |
| Vision quality drop without FT | H | Med | v1 uses Option C (frozen vision); accepted; iterate v2 with synth data |
| OOM under concurrency spike | M | High | `--max-num-seqs 4` cap; backend rate limiter; queue requests |
| Catastrophic forgetting Vietnamese | L | High | Eval set has 50% VN; gate at P4; LoRA r=16 limits damage |
| GPU thermal shutdown | L | High | Monitor temp; fan curve; alert at 85°C |
| Model drift after long uptime | L | Low | Restart container weekly via cron |
| Disk fills with logs | M | Med | Logrotate config for `logs/qa_history.jsonl` |

## Rollback plan

**Tier 1 — config-only** (instant, < 60s):
- Set `TUTOR_PROVIDER_OVERRIDE=` (empty) and restart backend OR
- Set `TUTOR_KILL_SWITCH=true` (no restart needed if hot-reload is on)
- All traffic returns to fallback provider

**Tier 2 — disable fallback wrapper** (5 min):
- Concrete feature flag: `TUTOR_DISABLE_FALLBACK_WRAPPER=true` (NEW
  setting in `Settings`, defaults `False`). When true,
  `get_context_and_stream_langgraph` skips `_stream_with_fallback` and
  goes directly through `_get_compiled_graph(settings.model_provider)`
  with no fallback logic.
- Use when fallback wrapper itself is buggy (e.g., causing double-billing,
  log spam, or stream corruption)
- Add this flag to `.env.example` and `docker-compose.yml` env block in
  the same commit as `_stream_with_fallback`

**Tier 3 — full revert** (30 min):
- `git revert` the codebase changes commit (single squashed commit per P7)
- Redeploy backend
- Stop `tutor-llm` container

## Stage promotion metrics — structured schema

Stage gates rely on a structured metrics log, not text grep. Backend
emits one JSON line per request to `logs/tutor_metrics.jsonl`:

```json
{
  "ts": "2026-04-27T10:15:30Z",
  "request_id": "uuid",
  "lecture_id": "...",
  "provider_selected": "self_hosted" | "google_genai",
  "fallback_triggered": true | false,
  "fallback_reason": null | "pre_flight_unreachable" | "capacity_guard" | "kill_switch" | "stream_error_pre_first_token",
  "kill_switch_active": false,
  "first_token_ms": 850,
  "total_stream_ms": 4200,
  "tokens_emitted": 312,
  "had_image": false,
  "tool_calls_emitted": 0,
  "http_status": 200,
  "error_class": null
}
```

Stage promotion gates query this file (or its loki/prom export) with
explicit filters, e.g.:
- `5xx rate` = `count(http_status >= 500) / count(*) over window`
- `Fallback rate` = `count(fallback_triggered=true) / count(*) over window`
- `p95 first-token` = percentile of `first_token_ms` over window
- `Capacity guard hit rate` = `count(fallback_reason="capacity_guard") / count(*)`

This replaces ad-hoc text-log searches and makes the gates objective.

## Operational runbook

### Restart tutor-llm
```bash
docker compose restart tutor-llm
# wait healthcheck:
docker compose ps tutor-llm
docker logs al_tutor_llm --tail 50
```

### Update model weights (new fine-tune)
```bash
# 1. Train new model → models/tutor-vl3b-v2-awq/
# 2. Update mount in docker-compose.yml or symlink:
ln -sfn tutor-vl3b-v2-awq fine-tune-chatbot/models/tutor-current
# 3. Restart
docker compose restart tutor-llm
```

### Diagnose slow responses
1. `nvidia-smi -l 2` — check GPU util / mem
2. `docker logs al_tutor_llm --since 5m` — look for queue warnings
3. Lower `--max-num-seqs` if KV cache thrashing
4. Check transcript window size — long contexts dominate latency

### Diagnose tool-call failures
1. Check vLLM logs for parser errors
2. Reproduce with `curl` (Test 4 in `05-serving-vllm.md`)
3. If parser broken: temporarily set `TUTOR_PROVIDER_OVERRIDE=` to force Gemini
4. Long-term: more tool-call data in next training run

## Post-launch v2 backlog

Track in `.planning/backlog/` after v1 ships:

- [ ] Move router off Gemini onto a tiny self-hosted classifier (3B-VL or
      smaller embedding-based)
- [ ] Vision FT with full Option B synthetic data
- [ ] Speculative decoding (vLLM `--speculative-model`) for latency
- [ ] Prefix caching for repeated system prompts
- [ ] DPO with thumbs-up/down signals from UI
- [ ] Multi-LoRA serving (one LoRA per course/domain)
- [ ] Move to Qwen2.5-VL-7B when GPU upgraded

## Exit criteria for v1 completion

- [ ] 100% traffic on `tutor-v1` for 7 consecutive days
- [ ] All metrics within thresholds
- [ ] Fallback rate <2%
- [ ] Judge score holds vs Stage 0 baseline
- [ ] Runbook validated by another engineer
- [ ] v2 backlog written
