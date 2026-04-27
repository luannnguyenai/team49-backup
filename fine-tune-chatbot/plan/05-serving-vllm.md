# P6 — Serving (vLLM Docker)

**Goal**: run `tutor-v1` as an OpenAI-compatible streaming endpoint with
tool calling and vision support, integrated into the existing
`docker-compose.yml`.

**Duration**: 0.5 day.

## Service design

Two deployment topologies are supported. Pick one based on where the backend runs:

### Topology A — Co-located (backend + vLLM on same host)

```
┌──────────┐  HTTP /v1/*   ┌──────────────┐
│ backend  │──────────────▶│  tutor-llm   │  ← vLLM, GPU
│ (FastAPI)│   OpenAI-     │  Qwen2.5-VL  │
└──────────┘   compatible  └──────────────┘
```

- Same docker network (`al_internal`)
- Backend reaches it as `http://tutor-llm:8000/v1`
- Host port `8001` exposed for debugging only
- `SELF_HOSTED_BASE_URL=http://tutor-llm:8000/v1`

### Topology B — Split (backend on VPS, vLLM on home GPU box) — used in FAST variant

```
[VPS — public]                                [Home — RTX 5060 Ti 16GB]
┌─────────────────┐                           ┌──────────────────────────┐
│ frontend +      │  HTTPS  ┌──────────────┐  │ vLLM container           │
│ FastAPI backend │────────▶│ Cloudflare   │─▶│ Qwen2.5-VL-3B + LoRA     │
│                 │         │ Tunnel (free)│  │ localhost:8000           │
└─────────────────┘         └──────────────┘  └──────────────────────────┘
```

The home GPU box does **not** need a public IP, port-forward, or static
DNS. Cloudflare Tunnel runs an outbound-only persistent connection to
Cloudflare; vLLM stays bound to `127.0.0.1:8000`. The VPS calls a public
Cloudflare URL which Cloudflare proxies into the tunnel.

- Backend (VPS) sets `SELF_HOSTED_BASE_URL=https://tutor-llm.<your-cf-subdomain>.example.com/v1`
- vLLM container exposes only to `127.0.0.1:8000` on the home box
- Optional: restrict tunnel to `Cf-Access-Client-Id` header bearing a service token
  to prevent random internet probes from hitting your model

This is the recommended topology for v1 FAST: **$0/month**, no port-forward,
no public IP exposure of the GPU box, and integrates without changing
backend code (only the env var differs from Topology A).

## docker-compose addition

Append to `docker-compose.yml` (do NOT add to `docker-compose.prod.yml` yet —
ship in dev first):

```yaml
  tutor-llm:
    image: vllm/vllm-openai:${VLLM_IMAGE_TAG}   # set after P1 verifies Blackwell support
    container_name: al_tutor_llm
    restart: unless-stopped
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./fine-tune-chatbot/models/tutor-current:/model:ro    # symlink; swap on update
      - tutor_hf_cache:/root/.cache/huggingface
    environment:
      VLLM_ATTENTION_BACKEND: ${VLLM_ATTENTION_BACKEND:-FLASH_ATTN}
      HF_HUB_OFFLINE: "1"
    command:
      - "--model"
      - "/model"
      - "--served-model-name"
      - "tutor-v1"
      - "--quantization"
      - "${TUTOR_QUANTIZATION:-awq_marlin}"   # set per P5 decision tree
      - "--max-model-len"
      - "4096"   # MUST match training `max_seq_length`; only raise after long-ctx eval pass
      - "--max-num-seqs"
      - "4"
      - "--gpu-memory-utilization"
      - "0.85"
      - "--enable-auto-tool-choice"
      - "--tool-call-parser"
      - "hermes"
      - "--limit-mm-per-prompt"
      - "image=1"
      - "--trust-remote-code"
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/v1/models"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s   # model load on cold start can take ~60s
    networks:
      - al_internal

volumes:
  tutor_hf_cache:
```

Verify the existing `volumes:` and `networks:` blocks already define the
relevant entries (read `docker-compose.yml` first; only add new volume).

## Why these flags

| Flag | Reason |
|---|---|
| `--quantization awq_marlin` | Fast Int4 kernel on Blackwell |
| `--max-model-len 4096` | Matches training `max_seq_length` (locked at 4096 in `03-finetune.md`). 4K covers TOC + transcript window + Q + answer. Raise only after explicit long-ctx eval that proves attention quality holds. |
| `--max-num-seqs 4` | KV cache fits ~4 concurrent on 16GB; tune via load test |
| `--gpu-memory-utilization 0.85` | Leave 15% for desktop / driver |
| `--enable-auto-tool-choice` | vLLM picks tool calls when model emits them |
| `--tool-call-parser hermes` | Qwen2.5 uses Hermes-style tool format |
| `--limit-mm-per-prompt image=1` | One image per request matches our use case (saves VRAM) |
| `--trust-remote-code` | Qwen VL has custom modeling code |

## Smoke tests

After `docker compose up -d tutor-llm`:

### Test 1 — health
```bash
curl http://localhost:8001/v1/models
# → {"data":[{"id":"tutor-v1",...}]}
```

### Test 2 — text streaming
```bash
curl -N http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tutor-v1",
    "messages": [{"role":"user","content":"Định lý Pytago là gì?"}],
    "stream": true
  }'
```

### Test 3 — vision (base64)
```bash
B64=$(base64 -w 0 sample_lecture.jpg)
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"tutor-v1\",
    \"messages\": [{\"role\":\"user\",\"content\":[
      {\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/jpeg;base64,$B64\"}},
      {\"type\":\"text\",\"text\":\"Mô tả slide.\"}
    ]}]
  }"
```

### Test 4 — tool calling
```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"tutor-v1",
    "messages":[{"role":"user","content":"Tính tổng các số nguyên tố nhỏ hơn 100."}],
    "tools":[{
      "type":"function",
      "function":{
        "name":"execute_python",
        "description":"Run Python code in sandbox.",
        "parameters":{"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}
      }
    }],
    "tool_choice":"auto"
  }'
```

Expect a response with `tool_calls[].function.name == "execute_python"` and
valid Python in `arguments.code`.

## Tunnel exposure (Topology B only)

Skip this section if Topology A.

### Quick start (ephemeral URL, dev only)

```bash
# On home box
cloudflared tunnel --url http://localhost:8001
```

Outputs a `https://<random>.trycloudflare.com` URL. Use for the first
end-to-end smoke from VPS. URL changes on every restart — not for production.

### Named tunnel (stable URL, recommended for v1)

```bash
# One-time setup on home box
cloudflared tunnel login                              # browser auth to Cloudflare
cloudflared tunnel create tutor-llm                   # creates UUID
# Add DNS record: tutor-llm.<your-domain> → tunnel UUID
cloudflared tunnel route dns tutor-llm tutor-llm.<your-domain>

# Config at ~/.cloudflared/config.yml
cat <<EOF > ~/.cloudflared/config.yml
tunnel: <UUID>
credentials-file: /home/<user>/.cloudflared/<UUID>.json
ingress:
  - hostname: tutor-llm.<your-domain>
    service: http://localhost:8001
  - service: http_status:404
EOF

# Run as service
cloudflared tunnel run tutor-llm
# Optionally: install as systemd unit (Linux) or NSSM service (Windows)
sudo cloudflared service install
```

### Lock down with Cloudflare Access (REQUIRED for any non-local-dev deployment)

⚠️ **Not optional outside of local dev.** Without Access, the tunnel URL
is a public unauthenticated GPU endpoint. Anyone who finds it (subdomain
guesses, leaked log lines, browser history, GitHub Issues) can run
inference on your hardware indefinitely, exhausting VRAM, electricity,
and home internet. There is no rate limit at the model layer by default.

Required for any deployment beyond local dev (incl. team demo, internal
testing, FAST 3-day MVP):

1. Create a Service Token in Cloudflare Zero Trust → Access → Service Auth
2. Create an Access Application for `tutor-llm.<your-domain>` requiring that
   service token in headers `Cf-Access-Client-Id` + `Cf-Access-Client-Secret`
3. On VPS, store both as env vars; backend sends them as headers when
   calling vLLM. LangChain `ChatOpenAI` accepts `default_headers` kwarg —
   plumb through `chat_model_factory.py`'s `self_hosted` branch:

```python
if provider == "self_hosted":
    headers = {}
    if settings.self_hosted_cf_access_id:
        headers["CF-Access-Client-Id"] = settings.self_hosted_cf_access_id
        headers["CF-Access-Client-Secret"] = settings.self_hosted_cf_access_secret
    kwargs = {
        "model": model,
        "model_provider": "openai",
        "temperature": temperature,
        "base_url": settings.self_hosted_base_url,
        "api_key": settings.self_hosted_api_key or "dummy",
        "default_headers": headers,
    }
```

### Tunnel resilience

- Cloudflare Tunnel auto-reconnects on dropped link; backend should retry
  on transient 502/504 (LangChain's default retry covers this)
- Latency overhead: typically +30–80ms RTT depending on PoP location
- Free tier limits: no published bandwidth cap for Tunnel itself; Cloudflare
  Workers free tier is separate and not used here
- Outage mode: if home box is offline, tunnel returns 502; `_stream_with_fallback`
  in `llm_service.py` (P7) catches this and falls back to Gemini

### Smoke test from VPS

```bash
# From VPS shell
curl https://tutor-llm.<your-domain>/v1/models
# Should return same payload as the local 8001 test
```

If the VPS gets `200` and the same model list, end-to-end path is verified.

## Load test (baseline-first, then set thresholds)

⚠️ **Do NOT freeze threshold targets before measuring baseline.** Targets
below are starting hypotheses; actual targets depend on:
- Home upload bandwidth (tunnel egress is your bottleneck for streaming)
- Cloudflare PoP-to-VPS RTT (varies +30–80ms by geography)
- 5060 Ti AWQ/bnb/BF16 throughput (differs per quantization tier)
- Concurrency-vs-latency tradeoff at chosen `--max-num-seqs`

Procedure:
1. Run `scripts/serving/load_test.py` against the local vLLM port (8001)
   for the LOCAL baseline; record p50/p95/throughput per concurrency level
   1, 2, 4, 8.
2. Re-run the same script targeting the Cloudflare Tunnel URL from the
   VPS for the END-TO-END baseline; the delta is the tunnel overhead.
3. Commit both result tables to `eval/load_test_baseline.md`.
4. Set production thresholds = local baseline × 1.5 (or end-to-end
   baseline × 1.2, whichever is larger), recorded in
   `eval/load_test_thresholds.md`.

Starting hypothesis (revise with actual data):

| Metric | Hypothesis | Notes |
|---|---|---|
| p50 first-token (local) | < 1s | Achievable on 5060 Ti BF16 at concurrency 2 |
| p50 first-token (via tunnel) | < 1.5s | +500ms overhead realistic in worst PoP |
| p95 first-token (via tunnel) | < 4s | Tunnel jitter + concurrency contention |
| p50 throughput | > 30 tok/s | At concurrency 2; lower at 4 |
| Concurrency without errors | ≥ 2 (BF16) / ≥ 4 (AWQ) | Tier-dependent |

If concurrency at chosen tier fails: lower `--max-num-seqs` or
`--max-model-len`, or step down to lower compression tier (re-run §
"Quantization feasibility ladder" in `04-eval-quantize.md`).

## Production hardening (post v1)

Defer to v2:
- Move to `docker-compose.prod.yml` with `--swap-space 4` and explicit shm
- Prometheus metrics scrape (`--port-metrics 8000` then scrape `/metrics`)
- Multi-replica with NGINX in front (only if traffic warrants — single GPU
  doesn't help)
- Persistent KV cache via `--enable-prefix-caching` (huge win for repeated
  system prompts — turn on once stable)

## Exit criteria

- [ ] `docker compose up tutor-llm` runs healthy
- [ ] All 4 smoke tests pass
- [ ] Load test: 4 concurrent streams stable for 10 min
- [ ] No restart loops, no OOM kills
- [ ] Logs: no "kernel image" errors (Blackwell verified)
