# GPT Review — Kế hoạch fine-tune Qwen2.5-VL-3B-Instruct

Ngày review: 2026-04-27

Phạm vi đọc:
- `plan/README.md`
- `plan/01-environment.md`
- `plan/02a-data-audit.md`
- `plan/02b-domain-data.md`
- `plan/02-data-pipeline.md`
- `plan/03-finetune.md`
- `plan/04-eval-quantize.md`
- `plan/05-serving-vllm.md`
- `plan/06-codebase-changes.md`
- `plan/07-rollout.md`
- `plan/datasets.md`
- `plan/gpt_response.md`

## Kết luận ngắn

Kế hoạch hiện tại **đủ tốt để bắt đầu P1/P2 audit**, nhưng **chưa nên chạy full fine-tune hoặc sửa codebase ngay**.

Điểm mạnh lớn nhất:
- Chọn Qwen2.5-VL-3B-Instruct là hợp lý cho GPU 16GB nếu chấp nhận chất lượng thấp hơn Gemini.
- P1 đặt đúng rủi ro critical path: Blackwell `sm_120`, PyTorch/Unsloth/bitsandbytes/vLLM.
- Data plan đã tốt hơn bản cũ: có P2a audit, có domain data từ course assets, có KG-derived data, có data governance.
- Eval plan đã có deterministic gates trước LLM judge.
- Code integration plan đã nhận diện đúng vấn đề provider-specific graph cache và fallback trước khi stream.

Điểm còn nguy hiểm:
- Có mâu thuẫn giữa số lượng sample, tỷ lệ tool-call, FAST timeline, và năng lực 3B model.
- Một số command/package/version có khả năng sai hoặc chưa được verify, đặc biệt Unsloth + Qwen2.5-VL + Blackwell + AWQ.
- Tool calling qua vLLM Hermes parser chưa chắc tương thích trực tiếp với ChatML `tool_calls` field như plan giả định.
- Shadow mode trong `06-codebase-changes.md` vẫn là blocking/sync style, có thể làm chậm request thật nếu gọi sai chỗ.
- Security của Cloudflare Tunnel và self-hosted endpoint chưa đủ cứng nếu đi production.

Khuyến nghị quyết định:
1. Cho phép chạy **P1 environment smoke** ngay.
2. Cho phép chạy **P2a data audit** ngay.
3. Chưa chạy P2b synthetic generation hàng loạt trước khi có số liệu audit thật.
4. Chưa sửa `llm_service.py`/provider graph trước khi P1 + P4/P5 proof pass.
5. Chưa đặt mục tiêu 3 ngày nếu muốn production-quality; FAST chỉ nên coi là MVP/research.

## Các vấn đề bắt buộc sửa trước khi execute full plan

### 1. FAST timeline 3 ngày quá lạc quan

Vấn đề:
- FAST variant gom data generation, environment, fine-tune, eval, quantize, vLLM, Cloudflare Tunnel, code integration, E2E vào 3 ngày.
- Với Blackwell `sm_120`, mọi thứ phụ thuộc vào wheel/kernel. Chỉ riêng vLLM source build hoặc Unsloth lỗi kernel đã có thể ăn hết 1 ngày.
- Data pipeline có nhiều script chưa tồn tại. KG parsing, MCQ conversion, Gemini generation, translation, dedupe, split, manifest, eval fixtures đều là implementation thật, không phải việc cấu hình đơn giản.

Nguyên nhân:
- Kế hoạch đang ước lượng theo "happy path".

Fix:
- Ghi rõ:
  - FAST 3 ngày = demo/research only, no production promise.
  - Production FULL = thực tế hơn: 8–12 ngày làm việc + shadow/canary.
  - Nếu P1 phải build vLLM từ source hoặc Unsloth lỗi, timeline tự động chuyển sang fallback schedule.

### 2. Tool-call percentage bị tính chưa nhất quán

Vấn đề:
- `02-data-pipeline.md` yêu cầu tool-call samples ≥25% training set.
- `02b-domain-data.md` FULL mix ~18k sample có Hermes 2000 + xLAM 500 + organic est. 30%.
- Nếu organic post-clean chỉ 3000 và 30% có tool: tool total ≈ 2000 + 500 + 900 = 3400 / 18000 = 18.9%, không đạt 25%.
- `datasets.md` FAST mix cũng ghi tool-call ≥25%, nhưng bảng FAST chỉ có Hermes 1000/10000 = 10%, trừ khi các math-with-code sample cũng được convert thành real tool-call format. Plan chưa nói rõ.

Nguyên nhân:
- Đang trộn "math/code reasoning" với "actual tool-call training sample". Hai loại này không tương đương.

Fix:
- Tách metric:
  - `has_tool_call=true` thực sự có assistant `tool_calls`.
  - `code_reasoning=true` chỉ có lời giải/code trong text.
- Update mixing recipe để `has_tool_call=true` đạt ngưỡng:
  - FULL: tăng Hermes/xLAM/synthetic tool-call lên 4500–5500 sample nếu tổng vẫn 18k.
  - FAST: nếu target 10k, cần ít nhất 2500 real tool-call sample, không phải 1000.

### 3. ChatML/tool-call format cần test bằng vLLM trước khi train

Vấn đề:
- Plan dùng Qwen2.5-VL ChatML + `tool_calls` JSON field + vLLM `--tool-call-parser hermes`.
- Hermes parser thường kỳ vọng format model output phù hợp Hermes tool call syntax. Không chắc fine-tune trên `tool_calls` field sẽ làm model emit đúng text/token format mà vLLM parser cần.
- Nếu format mismatch, model có thể học tool-call nội bộ trong dataset nhưng vLLM không parse ra OpenAI-compatible `tool_calls`.

Nguyên nhân:
- Kế hoạch chưa có "format compatibility proof" trước full training.

Fix:
- Thêm P1/P2 gate nhỏ:
  1. Tạo 20 sample tool-call đúng format dự kiến.
  2. Fine-tune tiny adapter 50–100 step hoặc prompt base model với tool schema.
  3. Serve qua vLLM với `--enable-auto-tool-choice --tool-call-parser hermes`.
  4. Xác nhận API response thật có `choices[].message.tool_calls`.
- Nếu fail, đổi converter sang Hermes XML/text format mà vLLM parser thực sự parse được.

### 4. Unsloth install command có rủi ro sai package extra

Vấn đề:
- `01-environment.md` dùng:
  ```bash
  uv pip install "unsloth[cu128] @ git+https://github.com/unslothai/unsloth.git"
  ```
- Extra `cu128` có thể không tồn tại hoặc thay đổi theo Unsloth release.
- Blackwell support có thể nằm ở `unsloth-zoo`, `xformers`, Triton, PyTorch nightly, hoặc bản wheel khác.

Nguyên nhân:
- Plan dựa vào giả định package naming.

Fix:
- Trong P1, chuyển command thành "candidate", không phải locked.
- Thêm bước verify theo official Unsloth docs tại thời điểm chạy.
- Output bắt buộc:
  - `env-frozen.txt`
  - `install-notes.md` ghi command thật đã chạy
  - `smoke_results.json` ghi torch capability, bnb availability, Unsloth model load, vLLM load.

### 5. AWQ/VLM path vẫn còn quá rủi ro

Vấn đề:
- `04-eval-quantize.md` đã cảnh báo AWQ for VLM tricky, nhưng toàn bộ serving plan vẫn ưu tiên AWQ Marlin.
- Qwen2.5-VL có vision tower/projector riêng. Offline AWQ có thể quantize language tower nhưng break load path, vision path, hoặc remote code config.
- Calibration đang text-only dù plan muốn vision support.

Nguyên nhân:
- Quantization được coi là implementation step, trong khi nó là feasibility risk.

Fix:
- Đổi P5 thành "Quantization feasibility experiment", không phải "produce AWQ target".
- Bắt buộc test 4 mode theo thứ tự:
  1. merged BF16/FP16 in vLLM, no quant
  2. bitsandbytes load-format in vLLM
  3. AWQ
  4. GPTQ
- Chọn mode bằng dữ liệu thực: load success, text smoke, vision smoke, tool-call smoke, p95 latency, VRAM.
- Không sửa backend integration trước khi ít nhất một serving mode pass.

### 6. Data governance mâu thuẫn nhẹ với synthetic generation

Vấn đề:
- README nói "Local-only training data" và không upload QA history/DB exports/lecture assets.
- `02b-domain-data.md` lại gửi transcripts/MCQs tới Gemini Flash vì là public Stanford courseware.
- Điều này có thể đúng, nhưng cần phân loại rõ "course assets public" vs "student QA/private".

Nguyên nhân:
- Governance đang viết chung cho nhiều loại dữ liệu.

Fix:
- Tạo bảng policy:
  - `student_qa`: local only, never external API.
  - `db_exports`: local only.
  - `public_course_transcripts`: allowed to Gemini if license/legal accepts.
  - `public MCQ/course artifacts`: allowed only if source license permits derivative/synthetic use.
  - `model weights trained on course data`: not redistributed.
- Manifest phải ghi `external_api_used=true/false` theo source.

### 7. License risk của external datasets chưa được chặn bằng gate cứng

Vấn đề:
- `datasets.md` có cảnh báo CC-BY-NC/research-only, nhưng mixing recipe vẫn liệt kê nhiều dataset có thể cần kiểm tra license.
- Nếu sản phẩm có commercial/paid deployment, NC dataset không được dùng.

Nguyên nhân:
- License audit là checklist, chưa là blocking gate.

Fix:
- Thêm `license_allowlist.json`.
- Build script phải fail nếu dataset license không thuộc allowlist cho deployment mode hiện tại.
- Thêm env/config:
  - `DEPLOYMENT_SCOPE=research|internal|commercial`
- Với `commercial`, tự động exclude CC-BY-NC/unknown.

### 8. P2b KG synthetic data có nguy cơ tạo "style tốt nhưng grounding yếu"

Vấn đề:
- KG-derived Q&A tạo nhiều sample dựa trên KP description/edges.
- Nếu KG descriptions ngắn, không đủ evidence transcript, model có thể học trả lời tự tin nhưng thiếu timestamp/citation grounding.
- E.3 deep-dive dùng Gemini có thể invent derivation/proof nếu input KG không đủ.

Nguyên nhân:
- KG là metadata graph, không phải full lecture evidence.

Fix:
- Với mọi KG sample, thêm `_meta.grounding_level`:
  - `kg_only`
  - `kg_plus_transcript`
  - `mcq_evidence`
  - `teacher_synthetic`
- Không dùng `kg_only` để train citation timestamp.
- E.3 prompt phải yêu cầu "nếu KG không đủ thông tin, không thêm derivation ngoài input".
- Eval cần category riêng cho KG-only hallucination.

### 9. Vision v1 đang bị kỳ vọng hơi cao

Vấn đề:
- Kế hoạch freeze vision tower, chỉ dùng 200–500 vision retention samples.
- Nhưng README vẫn có vision subset gate vs Gemini baseline, chỉ cho phép kém tối đa 0.5 điểm.
- Với lecture slides nhiều chữ/công thức, base Qwen VL 3B có thể không đủ OCR/diagram quality.

Nguyên nhân:
- V1 đang vừa muốn "skip vision FT" vừa muốn "vision production quality".

Fix:
- Ghi rõ v1 vision mục tiêu là:
  - preserve base vision ability,
  - không hallucinate,
  - mô tả slide cơ bản,
  - không cam kết ngang Gemini VLM.
- Nếu product cần vision tutor nghiêm túc, Option B không còn optional; phải tạo 2k–5k slide-grounded vision samples và có eval riêng.

### 10. Code integration plan cần kiểm tra thực tế với code hiện tại trước khi apply

Vấn đề:
- `06-codebase-changes.md` mô tả full replacement logic cho `llm_service.py`, nhưng file hiện tại có thể đã thay đổi so với plan.
- Những symbol như `compiled_graph`, `_get_llm_with_tools`, `graph_builder`, `call_model`, `_save_qa_history` cần được inspect + GitNexus impact trước khi sửa.
- Plan nói source files touched 4, nhưng exit criteria vẫn ghi "All 3 file changes applied"; còn sót wording.

Nguyên nhân:
- Plan là conceptual diff, chưa phải patch dựa trên code hiện tại.

Fix:
- Trước P7:
  - chạy GitNexus impact cho từng symbol như plan yêu cầu;
  - đọc code thật;
  - viết patch nhỏ theo current code, không copy full pseudo-code;
  - sửa exit criteria "3 file changes" thành danh sách thật.

### 11. Shadow mode có thể làm request thật chậm hoặc block event loop

Vấn đề:
- `06-codebase-changes.md` `_shadow_log` chạy graph.stream và collect messages.
- `07-rollout.md` nói fire-and-forget async, nhưng P7 implementation chưa bảo đảm fire-and-forget thật.
- Nếu gọi sau `_save_qa_history` trong request path mà không background task/thread, user request có thể bị chậm đáng kể.

Nguyên nhân:
- Shadow design chưa quyết định sync vs async vs queue.

Fix:
- V1 đơn giản hơn:
  - Không chạy shadow trong cùng request path.
  - Log input + primary answer.
  - Background worker/offline script replay sample qua self-hosted và judge.
- Nếu vẫn muốn online shadow:
  - dùng `asyncio.create_task` nếu call stack async thật;
  - đặt timeout ngắn;
  - không bao giờ await shadow trước khi trả response;
  - không log full PII.

### 12. Cloudflare Tunnel endpoint cần auth mặc định, không optional

Vấn đề:
- `05-serving-vllm.md` để Cloudflare Access là optional.
- Nếu tunnel URL bị lộ, ai cũng có thể dùng model endpoint, gây GPU abuse/cost/availability issue.

Nguyên nhân:
- Topology B đang tối ưu nhanh và miễn phí, chưa đủ production security.

Fix:
- Với bất kỳ deployment ngoài dev:
  - Cloudflare Access service token là bắt buộc.
  - Backend phải gửi `CF-Access-Client-Id` và `CF-Access-Client-Secret`.
  - Secrets không ghi vào logs.
  - vLLM nên có API key nếu layer server hỗ trợ.
- Thêm health check từ VPS qua tunnel có auth header.

### 13. Rate limiter bypass cho self-hosted có thể gây OOM

Vấn đề:
- `llm_rate_limiter.py` bypass hoàn toàn cho `self_hosted`.
- Đúng là không có external API quota, nhưng local GPU có concurrency/VRAM quota.

Nguyên nhân:
- Đang nhầm "API quota" với "capacity control".

Fix:
- Không dùng Gemini quota limiter cho self-hosted, nhưng cần local concurrency limiter:
  - semaphore/queue ở backend cho self-hosted tutor requests;
  - hoặc rely vào vLLM queue nhưng backend vẫn nên có timeout/backpressure;
  - alert nếu queue quá dài.
- Plan nên đổi wording: "bypass external quota limiter, add/verify local capacity guard".

### 14. Eval leakage risk cần cụ thể hơn

Vấn đề:
- MCQ-derived samples, translated MCQs, KG synth, held-out test có nguy cơ overlap/paraphrase.
- Plan có MinHash train/test, nhưng chưa nêu split theo source entity.

Nguyên nhân:
- Nếu cùng một MCQ/KP sinh nhiều variants rồi random split, train và test leak cùng concept/stem.

Fix:
- Split theo group key trước khi expand variants:
  - MCQ: `item_id`
  - KG: `kp_id`
  - transcript: `lecture_id + time_window`
  - organic: normalized question hash
- Tất cả variants của cùng group phải nằm cùng split.
- Eval fixtures không lấy từ train source group.

### 15. Training config thiếu resume/reproducibility chi tiết

Vấn đề:
- `03-finetune.md` có seed và output dir, nhưng thiếu resume path, exact dataset manifest hash, command log, adapter versioning.

Nguyên nhân:
- Plan tập trung vào first successful run.

Fix:
- Mỗi run tạo:
  - `runs/<run_id>/config.yaml`
  - `runs/<run_id>/manifest_hash.txt`
  - `runs/<run_id>/train_command.sh`
  - `runs/<run_id>/metrics.json`
  - `runs/<run_id>/git_commit.txt`
- Checkpoint resume instruction:
  - `trainer.train(resume_from_checkpoint=True|path)`

## Nhận xét theo file

### `plan/README.md`

Tốt:
- Decision table rõ.
- Local-first đúng.
- Có fallback Gemini.
- Có data governance.

Cần sửa:
- FAST timeline cần disclaimer mạnh hơn.
- Success criteria vision nên tách "preserve base vision" và "domain slide VQA".
- Repository layout vẫn ghi `plan/gpt_response.md` là GPT review cũ; nếu file mới là `gpt-review.md` thì nên cập nhật sau.

### `plan/01-environment.md`

Tốt:
- P1 là critical path.
- Có smoke load, inference, train, vLLM.

Cần sửa:
- Install commands phải được verify với official docs tại thời điểm chạy.
- Không dùng `latest` cho vLLM sau khi P1 pass.
- Thêm WSL/Linux fallback nếu Windows native path fail.
- Ghi kết quả smoke vào file machine-readable.

### `plan/02a-data-audit.md`

Tốt:
- Audit trước extraction là đúng.
- Decision matrix rõ.

Cần sửa:
- Language detection bằng ký tự tiếng Việt quá thô; nhiều câu tiếng Việt không dấu sẽ bị tính `en/other`.
- Audit nên count duplicate, token length, image truncation length distribution.
- Commit `audit_report.json` cần đảm bảo không chứa PII/raw question.

### `plan/02b-domain-data.md`

Tốt:
- Dùng course assets/KG làm primary source là hướng đúng.
- Strategy A từ MCQ rất giá trị.
- KG strategy tạo coverage tốt.

Cần sửa:
- Cost Gemini Flash có thể thấp hơn thực tế nếu prompt chứa transcript dài; nên ghi budget range rộng hơn.
- KG samples cần grounding metadata.
- Split phải group by MCQ/KP/time window để tránh leakage.
- Tool-call ratio trong mix chưa đạt như claim.

### `plan/02-data-pipeline.md`

Tốt:
- Nhận diện image_base64 truncated blocker.
- Có PII scrub, dedupe, split stratified.

Cần sửa:
- PII scrub regex không đủ; cần at least audit samples sau scrub.
- Toxicity/off-topic filter dùng `detoxify` là dependency mới, phải kiểm tra install/fit.
- Output ChatML cho tool-call phải được validated bằng real vLLM parser.

### `plan/03-finetune.md`

Tốt:
- Hyperparams hợp lý cho 3B QLoRA.
- Có OOM fallback ladder.

Cần sửa:
- Thêm tiny overfit run chính thức trước full train.
- Tool-call validation không thể chỉ "at least one of 5 samples".
- Estimate 2–4h nên đổi thành target, không phải guarantee.
- Cần run metadata và resume instructions.

### `plan/04-eval-quantize.md`

Tốt:
- Deterministic Gate 1 tốt.
- Có baseline Gemini và base Qwen control.
- Có quantization decision tree.

Cần sửa:
- Gate `No "I don't know" when context contains answer ≥90%` cần định nghĩa deterministic matcher/rubric cụ thể.
- LLM judge phải blind/shuffled và log judge prompt/version.
- P5 nên bắt đầu bằng unquantized serving proof trước AWQ.

### `plan/05-serving-vllm.md`

Tốt:
- Topology A/B rõ.
- Smoke tests đủ loại: health, stream, vision, tools.

Cần sửa:
- `--max-model-len` table vẫn nói 8192 trong phần "Why these flags", trong compose command là 4096. Cần đồng bộ.
- Cloudflare Access không nên optional cho production.
- Load test target `p50 first-token <1s` có thể quá tham vọng qua tunnel + home GPU; nên đo baseline trước rồi set threshold.

### `plan/06-codebase-changes.md`

Tốt:
- Có GitNexus preflight, đúng rule repo.
- Provider-specific graph cache là hướng đúng.
- Không migrate router là quyết định tốt.

Cần sửa:
- Exit criteria còn ghi "All 3 file changes" dù scope là 10 files.
- Shadow implementation cần async/offline rõ.
- Rate limiter bypass cần kèm local capacity limiter.
- `_stream_with_fallback` dùng `next(stream)` với LangGraph stream cần verify kiểu iterator/chunk thực tế; test unit/integration bắt buộc.

### `plan/07-rollout.md`

Tốt:
- Có shadow, canary, kill switch, rollback, risk register.

Cần sửa:
- Shadow online nên chuyển thành offline replay nếu muốn đơn giản và an toàn.
- Stage promotion cần metric từ logs có schema cụ thể, không chỉ text log search.
- Tier 2 rollback "remove wrapper via feature flag" chưa có feature flag cụ thể.

### `plan/datasets.md`

Tốt:
- Có tiering, license warning, eval-only warning.
- Datasets phục vụ function calling/Vietnamese/math/vision hợp lý.

Cần sửa:
- License gate phải được enforce bằng script.
- Dataset existence/license cần verify tại runtime, không dựa vào note.
- FAST mix claim tool-call ≥25% chưa đúng nếu không convert math/code thành actual tool calls.

## Kế hoạch sửa đề xuất trước khi triển khai

### Blocker trước P1/P2a

Không có. Có thể chạy ngay:
- P1 environment smoke.
- P2a audit.

### Blocker trước full P2b/P3

Phải sửa:
1. Tool-call format compatibility proof.
2. Split by group key để tránh leakage.
3. License allowlist gate.
4. Governance table cho external API usage.
5. Tool-call ratio calculation.

### Blocker trước P7 code integration

Phải có:
1. P1 vLLM serving proof pass.
2. Một serving mode pass P5/P6 smoke: text + vision + tool + stream.
3. GitNexus impact analysis theo plan.
4. Patch dựa trên current code, không copy pseudo-code.
5. Tests cho provider selection, fallback pre-first-token, no fallback mid-stream, self-hosted capacity behavior.

## Go / No-Go

Go:
- Chạy P1.
- Chạy P2a.
- Làm tiny tool-call format proof.

No-Go tạm thời:
- Chưa full fine-tune.
- Chưa quantize AWQ như mặc định.
- Chưa sửa backend integration.
- Chưa production tunnel nếu chưa có Access auth.

## Final recommendation

Kế hoạch của Claude Opus đã tốt và có thể dùng làm base execution plan. Tuy nhiên cần coi đây là **engineering plan có nhiều feasibility gates**, không phải checklist tuyến tính.

Ưu tiên thực tế:
1. Prove local stack.
2. Prove vLLM tool-call parser format.
3. Audit data thật.
4. Build small clean dataset + tiny overfit.
5. Full train only after format/data gates pass.
6. Serving proof before backend code changes.
7. Rollout behind config + fallback + auth.
