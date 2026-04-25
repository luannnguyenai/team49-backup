# P5 — Serving (vLLM Docker)

**Goal**: run `tutor-v1` as an OpenAI-compatible streaming endpoint with
tool calling and vision support, integrated into the existing
`docker-compose.yml`.

**Duration**: 0.5 day.

## Service design

```
┌──────────┐  HTTP /v1/*   ┌──────────────┐
│ backend  │──────────────▶│  tutor-llm   │  ← vLLM, GPU
│ (FastAPI)│   OpenAI-     │  Qwen2.5-VL  │
└──────────┘   compatible  └──────────────┘
```

- Same docker network (`al_internal`)
- Backend reaches it as `http://tutor-llm:8000/v1`
- Host port `8001` exposed for debugging only

## docker-compose addition

Append to `docker-compose.yml` (do NOT add to `docker-compose.prod.yml` yet —
ship in dev first):

```yaml
  tutor-llm:
    image: vllm/vllm-openai:latest    # pin to a Blackwell-verified tag from P1
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
      - ./fine-tune-chatbot/models/tutor-vl3b-v1-awq:/model:ro
      - tutor_hf_cache:/root/.cache/huggingface
    environment:
      VLLM_ATTENTION_BACKEND: FLASHINFER   # if available; else FLASH_ATTN
      HF_HUB_OFFLINE: "1"
    command:
      - "--model"
      - "/model"
      - "--served-model-name"
      - "tutor-v1"
      - "--quantization"
      - "awq_marlin"
      - "--max-model-len"
      - "8192"
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
| `--max-model-len 8192` | Matches training ctx; 8K covers most lecture windows |
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

## Load test

`fine-tune-chatbot/scripts/serving/load_test.py` — fire 8 concurrent streaming
requests, measure:

| Metric | Target |
|---|---|
| p50 first-token latency | < 1s |
| p95 first-token latency | < 3s |
| p50 throughput | > 30 tok/s |
| Concurrency without errors | ≥ 4 |

If concurrency >4 fails: lower `--max-num-seqs` or `--max-model-len`.

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
