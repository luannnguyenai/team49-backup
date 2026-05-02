# PROPOSAL: Kế hoạch Fine-tune Chatbot bằng tiếng Anh

## 1. Mục tiêu

Proposal này đề xuất hướng fine-tune mới cho `fine-tune-chatbot` với 4 quyết định chính:

| Hạng mục | Đề xuất |
|---|---|
| Dataset domain chính | Giữ nguyên dataset hiện tại của dự án |
| Ngôn ngữ | Chuyển sang full tiếng Anh |
| Base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| External dataset | Dùng **ELI5 đã lọc** như dữ liệu phụ trợ, không dùng làm corpus chính |

Luận điểm trung tâm:

> ELI5 phù hợp để dạy mô hình cách giải thích dài, mạch lạc bằng tiếng Anh, nhưng không phù hợp để thay thế dataset domain hiện có. Với bài toán chatbot AI/ML/NLP/CV, ELI5 chỉ nên đóng vai trò dữ liệu phụ trợ cho explanation style.

---

## 2. Kết luận đề xuất

| Câu hỏi | Kết luận |
|---|---|
| Có nên dùng ELI5 không? | Có |
| Có nên dùng raw/full ELI5 không? | Không |
| ELI5 có nên là nguồn tri thức chính không? | Không |
| ELI5 nên dùng để làm gì? | Dạy cách trả lời giải thích dài bằng tiếng Anh |
| Dataset nào giữ vai trò chính? | Dataset hiện tại của dự án |
| Model phù hợp? | `Qwen/Qwen2.5-VL-3B-Instruct` |

---

## 3. Vì sao hướng hiện tại chưa đủ mạnh

Trong thư mục `fine-tune-chatbot`, hướng cũ chưa đủ thuyết phục vì external data đang được biện minh chủ yếu như một nguồn “instruction data bổ sung”, trong khi bài toán thật là một **domain tutor** cho AI/ML/NLP/CV.

### Vấn đề chính

| Vấn đề | Mô tả |
|---|---|
| External data quá generic | Không bám sát AI/ML/NLP/CV |
| Mục tiêu huấn luyện chưa tách rõ | Chưa phân biệt domain knowledge và explanation style |
| Benchmark chưa sát bài toán | Đang nghiêng về benchmark tổng quát hơn là tutor benchmark |

### Điều proposal mới cần làm rõ

| Câu hỏi cần trả lời | Trả lời trong proposal này |
|---|---|
| Dataset hiện tại dạy mô hình điều gì? | Dạy tri thức domain |
| ELI5 bổ sung điều gì? | Dạy phong cách giải thích dài bằng tiếng Anh |
| ELI5 không nên gánh vai trò gì? | Không làm nguồn tri thức chính |
| Thành công được đo bằng gì? | Held-out domain eval + benchmark domain-relevant |

---

## 4. Base model đề xuất

### Chọn mô hình

| Hạng mục | Lựa chọn |
|---|---|
| Base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| Hình thức fine-tune | QLoRA / LoRA |
| Loại dữ liệu | Text-first SFT trên vision-capable base, giữ nguyên research dataset hiện tại |
| Ngôn ngữ mục tiêu | English |

### Lý do chọn

| Lý do | Giải thích |
|---|---|
| Phù hợp quy mô | 7B là mức hợp lý để fine-tune thực tế |
| Mạnh về reasoning và instruction-following | Phù hợp chatbot kỹ thuật |
| Hỗ trợ ngữ cảnh dài | Hữu ích cho câu trả lời giải thích nhiều đoạn |
| Hệ sinh thái phổ biến | Dễ triển khai, dễ benchmark, dễ báo cáo |

---

## 5. Vai trò của dataset hiện tại và ELI5

### Phân vai dữ liệu

| Nguồn dữ liệu | Vai trò chính | Có nên là nguồn tri thức chính không? |
|---|---|---|
| Dataset hiện tại của dự án | Tri thức AI/ML/NLP/CV, phong cách course-specific | Có |
| ELI5 đã lọc | Long-form explanation style bằng tiếng Anh | Không |

### Ý nghĩa của cách phân vai này

| Thành phần | Dạy mô hình điều gì |
|---|---|
| Dataset hiện tại | “Nói cái gì” trong domain |
| ELI5 | “Giải thích như thế nào” bằng tiếng Anh |

Đây là điểm lập luận mạnh nhất của proposal.

---

## 6. Vì sao chọn ELI5

### Điểm mạnh của ELI5

| Điểm mạnh | Ý nghĩa với dự án |
|---|---|
| Long-form QA | Phù hợp chatbot cần trả lời giải thích dài |
| Nhiều câu hỏi kiểu why/how | Hợp với vai trò tutor |
| Dữ liệu tiếng Anh tự nhiên | Phù hợp định hướng full English |
| Có nền tảng học thuật mạnh | Dễ bảo vệ khi viết proposal |

### ELI5 giúp cải thiện nhóm năng lực nào

| Năng lực | ELI5 có giúp không? |
|---|---|
| Trả lời theo đoạn, mạch lạc | Có |
| Giải thích khái niệm bằng tiếng Anh | Có |
| Giữ giọng điệu “giảng giải” | Có |
| Tri thức chuyên sâu AI/ML/NLP/CV | Không đủ |
| Bám sát course material | Không |

---

## 7. Vì sao không nên dùng ELI5 làm dataset chính

| Rủi ro | Giải thích |
|---|---|
| General-domain | Chủ đề quá rộng, nhiều nội dung không liên quan |
| Chất lượng không đồng đều | Dữ liệu Reddit có nhiễu |
| Không course-grounded | Không bám CS224n/CS231n/CS230 hay tài liệu riêng của dự án |
| Có hạn chế benchmark đã được chỉ ra | Có overlap và metric LFQA chưa thật sự mạnh |

### Kết luận sử dụng

| Cách dùng | Có khuyến nghị không? |
|---|---|
| Dùng full ELI5 để train chính | Không |
| Dùng ELI5 làm auxiliary explanation corpus | Có |
| Dùng ELI5 dev/test để đo style | Có |

---

## 8. Preview dữ liệu ELI5

Dưới đây là preview rút gọn để minh họa kiểu dữ liệu của ELI5.

| Ví dụ | Question | Kiểu answer |
|---|---|---|
| A | `why chemical weapons are considered more indiscriminate than conventional weapons` | Giải thích nhiều câu về mức độ lan rộng, tồn dư và collateral damage |
| B | `in football, why waste the first two plays with a rush up the middle` | Giải thích reasoning chiến thuật, không chỉ đáp án ngắn |
| C | Prompt mở trong KILT-ELI5 | Một hoặc nhiều câu trả lời kèm provenance, nhưng vẫn cần lọc mạnh trước khi huấn luyện |

### Ý nghĩa của preview

| Quan sát | Kết luận |
|---|---|
| Câu hỏi thiên về giải thích | Hợp để dạy explanation behavior |
| Câu trả lời dài theo đoạn | Hợp để cải thiện long-form response |
| Chủ đề rất rộng | Không phù hợp dùng raw cho domain tutor |

---

## 9. Cách dùng ELI5 đúng cho dự án này

### Nguyên tắc sử dụng

| Nguyên tắc | Mô tả |
|---|---|
| Không dùng raw | Phải lọc kỹ trước khi huấn luyện |
| Không dùng toàn bộ | Chỉ lấy subset liên quan |
| Không dùng làm domain corpus | Dataset hiện tại vẫn là trục chính |
| Chỉ dùng để bù capability gap | Tập trung vào explanation style |

### Luật lọc dữ liệu đề xuất

| Nhóm lọc | Luật lọc |
|---|---|
| Loại câu hỏi | Ưu tiên `why`, `how`, `difference`, `what happens`, `how does` |
| Độ dài câu trả lời | Khoảng `120-450` từ |
| Chất lượng | Mạch lạc, giải thích rõ, ít noise |
| Topic | Science, math, computing, probability, optimization, NLP, CV, ML |
| Loại bỏ | Celebrity, sports, politics, entertainment, anecdotal answers, sarcasm |

### Topic filter gợi ý cho bài toán AI/ML/NLP/CV

| Cụm chủ đề nên ưu tiên |
|---|
| machine learning |
| deep learning |
| neural networks |
| probability |
| statistics |
| optimization |
| linear algebra |
| NLP / transformers / embeddings / language models |
| computer vision / CNN / segmentation / detection |
| algorithms / computation / information theory |

---

## 10. Tỷ lệ trộn dữ liệu đề xuất

| Thành phần | Tỷ lệ đề xuất |
|---|---|
| Dataset hiện tại của dự án | 65-75% |
| Filtered ELI5 subset | 20-30% |
| Dữ liệu cân bằng format / instruction khác nếu cần | 5-10% |

### Giải thích

| Quyết định | Lý do |
|---|---|
| Không vượt quá ~30% ELI5 ở v1 | Tránh domain drift |
| Giữ dataset dự án làm anchor | Bảo toàn tri thức AI/ML/NLP/CV |
| Tăng ELI5 chỉ khi cần | Chỉ tăng nếu explanation quality còn yếu |

---

## 11. Các paper liên quan và mức độ uy tín

### 11.1 Bảng phân loại độ uy tín

| Paper / nguồn | Venue | Peer review | Mức uy tín học thuật | Ghi chú sử dụng |
|---|---|---:|---|---|
| **ELI5: Long Form Question Answering** | ACL 2019 | Có | Rất cao | Paper gốc của ELI5 |
| **KILT: a Benchmark for Knowledge Intensive Language Tasks** | NAACL 2021 | Có | Rất cao | Đưa ELI5 vào benchmark lớn |
| **Hurdles to Progress in Long-form Question Answering** | NAACL 2021 | Có | Rất cao | Quan trọng vì chỉ ra hạn chế của ELI5 |
| **TheoremQA** | EMNLP 2023 | Có | Rất cao | Benchmark phù hợp technical reasoning |
| **MMLU** | ICLR 2021 | Có | Rất cao | Benchmark chuẩn, top ML venue |
| **MMLU-Pro** | NeurIPS 2024 Datasets & Benchmarks Track | Có | Rất cao | Bản nâng cấp mạnh của MMLU |
| **Read before Generate!** | Findings of ACL 2022 | Có | Cao | Dùng được, nhưng thấp hơn main conference |
| **WebGPT** | OpenAI Research page | Không chuẩn conference/journal | Trung bình | Chỉ nên dùng phụ trợ, không làm citation chính |
| Hugging Face dataset/model cards | Không phải paper | Không | Thấp | Chỉ dùng làm nguồn kỹ thuật |
| GitHub repo / blog | Không phải paper | Không | Thấp | Không dùng làm nguồn học thuật chính |

### 11.2 Xếp hạng venue lớn

| Venue | Loại | Mức xếp hạng tham khảo |
|---|---|---|
| ACL | Top conference NLP | A* |
| ICLR | Top conference ML | A* |
| NeurIPS | Top conference ML | A* |
| NAACL | Top conference NLP | A |
| EMNLP | Top conference NLP | A |

### 11.3 Nếu cần nguồn journal Q1 / WoS / Scopus

| Journal | Mức uy tín | Dùng để làm gì |
|---|---|---|
| **Transactions of the Association for Computational Linguistics (TACL)** | Q1, indexed in Web of Science | Bổ sung citation journal mạnh |
| **Computational Linguistics** | Q1 | Bổ sung citation journal mạnh |

### 11.4 Journal Q1 có nhắc trực tiếp đến ELI5

| Bài báo | Journal | Vai trò |
|---|---|---|
| **FeTaQA: Free-form Table Question Answering** | TACL 2022 | Nhắc ELI5 như long-form QA dataset quan trọng |
| **CLAPnq: Cohesive Long-form Answers from Passages in Natural Questions for RAG systems** | TACL 2025 | So sánh và nêu giới hạn của ELI5 trong grounded RAG |

### 11.5 Kết luận về nguồn học thuật

| Nhóm nguồn | Có nên dùng trong proposal không? |
|---|---|
| Top conference peer-reviewed | Có, nên là nguồn chính |
| Journal Q1 / WoS / Scopus | Có, rất nên bổ sung |
| Blog / model card / dataset card | Chỉ dùng phụ trợ |

---

## 12. Bộ benchmark phù hợp với bài toán AI/ML/NLP/CV

### 12.1 Nguyên tắc chọn benchmark

| Nguyên tắc | Ý nghĩa |
|---|---|
| Phải bám bài toán chatbot thật | Không dùng benchmark chung chung làm tiêu chí chính |
| Ưu tiên domain relevance | AI/ML/NLP/CV quan trọng hơn điểm tổng quát |
| Có benchmark nội bộ | Held-out set của chính dự án là quan trọng nhất |
| Có benchmark external để báo cáo học thuật | Tăng sức thuyết phục với giảng viên |

### 12.2 Benchmark stack đề xuất

| Tier | Benchmark | Vai trò |
|---|---|---|
| A | Held-out internal dataset | Shipping gate quan trọng nhất |
| B1 | MMLU selected subjects | Kiểm tra nền tảng kiến thức học thuật |
| B2 | MMLU-Pro | Kiểm tra độ khó và reasoning mạnh hơn |
| B3 | TheoremQA | Kiểm tra technical reasoning gần AI/ML |
| C | Filtered ELI5 dev/test | Chỉ đo explanation style bằng tiếng Anh |

### 12.3 Subject subset nên dùng trong MMLU

| Subject | Có nên dùng? | Lý do |
|---|---:|---|
| `machine_learning` | Có | Sát nhất với bài toán |
| `college_computer_science` | Có | Sát nền tảng CS |
| `college_mathematics` | Có | Quan trọng cho ML foundations |
| `high_school_statistics` | Có | Hữu ích cho xác suất, thống kê |
| `abstract_algebra` | Tùy chọn | Stress test lý luận |
| `formal_logic` | Tùy chọn | Stress test lập luận |

---

## 13. Benchmark nào không nên là tiêu chí chính

| Benchmark / cách dùng | Vì sao không nên là tiêu chí chính |
|---|---|
| Global MMLU score | Quá rộng, không sát AI/ML/NLP/CV tutor |
| GSM8K đơn lẻ | Quá hẹp, chỉ thiên về arithmetic reasoning |
| Generic chat benchmark | Không đo được khả năng giải thích khái niệm kỹ thuật |
| Raw ELI5 score | Dễ ưu tiên fluency hơn factual correctness |

---

## 14. Giao thức đánh giá

### 14.1 Trước fine-tune

Đánh giá base `Qwen/Qwen2.5-VL-3B-Instruct` trên:

| Bộ đánh giá |
|---|
| internal held-out domain set |
| MMLU selected subjects |
| MMLU-Pro |
| TheoremQA |
| filtered ELI5 dev/test |

### 14.2 Sau fine-tune

Chạy lại toàn bộ và so sánh delta.

### 14.3 Tiêu chí thành công

| Chỉ số | Kỳ vọng |
|---|---|
| Internal domain benchmark | Phải tăng |
| MMLU selected subjects | Không được giảm đáng kể |
| TheoremQA | Tăng nhẹ hoặc ít nhất không tụt mạnh |
| ELI5 style eval | Phải cải thiện rõ về explanation quality |

### 14.4 Quy tắc ra quyết định

| Tình huống | Kết luận |
|---|---|
| Internal domain tăng, MMLU giảm nhẹ | Có thể chấp nhận |
| ELI5 fluency tăng, domain correctness giảm | Loại run |
| Explanation không tăng rõ | Xem lại tỷ lệ ELI5 hoặc lọc ELI5 |

---

## 15. Kế hoạch triển khai trong repo này

### Phase 1: Chuẩn hóa dữ liệu

| Việc cần làm | Mục tiêu |
|---|---|
| Giữ nguyên dataset domain hiện tại | Làm anchor chính |
| Tạo filtered ELI5 subset | Bổ sung explanation style |
| Chuẩn hóa toàn bộ sang English | Đồng bộ mục tiêu huấn luyện |

### Phase 2: Tạo bộ eval

| File gợi ý | Vai trò |
|---|---|
| `domain_eval.jsonl` | Đánh giá domain chính |
| `eli5_style_eval.jsonl` | Đánh giá explanation style |
| `external_reasoning_eval.jsonl` | Đánh giá benchmark ngoài |

### Phase 3: Chạy ablation

| Run | Thành phần dữ liệu |
|---|---|
| A | Chỉ dataset dự án |
| B | Dataset dự án + 10% ELI5 |
| C | Dataset dự án + 20% ELI5 |
| D | Dataset dự án + 30% ELI5 |

### Ý nghĩa của ablation

| Mục đích | Lý do |
|---|---|
| Chứng minh ELI5 có ích thật hay không | Tránh kết luận cảm tính |
| Tìm tỷ lệ trộn tối ưu | Giảm nguy cơ domain drift |

---

## 16. Khuyến nghị cuối cùng

| Hạng mục | Khuyến nghị cuối cùng |
|---|---|
| Dataset chính | Dataset hiện tại của dự án |
| Base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| Ngôn ngữ | Full English |
| Vai trò của ELI5 | Auxiliary explanation dataset đã lọc |
| Benchmark chính | Held-out internal AI/ML/NLP/CV set |
| Benchmark học thuật phụ | MMLU selected subjects, MMLU-Pro, TheoremQA |
| Benchmark phong cách | Filtered ELI5 dev/test |

### Kết luận tổng hợp

Proposal mạnh nhất cho dự án này không phải là:

> “Dùng ELI5 vì nó lớn.”

Mà phải là:

> “Giữ dataset hiện tại làm nguồn tri thức domain chính, và dùng ELI5 đã lọc để bù đúng khoảng trống về phong cách giải thích dài bằng tiếng Anh; sau đó đánh giá bằng benchmark bám sát bài toán AI/ML/NLP/CV.”

Đây là cách lập luận chặt hơn, đúng học thuật hơn, và dễ thuyết phục giảng viên hơn.

---

## 17. Nguồn tham khảo chính

### 17.1 Paper / venue học thuật

| Tên | Link |
|---|---|
| ELI5 (ACL 2019) | https://aclanthology.org/P19-1346/ |
| KILT (NAACL 2021) | https://aclanthology.org/2021.naacl-main.200/ |
| Hurdles to Progress in LFQA (NAACL 2021) | https://aclanthology.org/2021.naacl-main.393/ |
| TheoremQA (EMNLP 2023) | https://aclanthology.org/2023.emnlp-main.489/ |
| MMLU (ICLR 2021) | https://openreview.net/forum?id=d7KBjmI3GmQ |
| MMLU-Pro (NeurIPS 2024) | https://proceedings.neurips.cc/paper_files/paper/2024/hash/ad236edc564f3e3156e1b2feafb99a24-Abstract-Datasets_and_Benchmarks_Track.html |
| FeTaQA (TACL 2022) | https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00446/109273/FeTaQA-Free-form-Table-Question-Answering |
| CLAPnq (TACL 2025) | https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00729/127456/CLAPnq-Cohesive-Long-form-Answers-from-Passages-in |

### 17.2 Xếp hạng venue / journal

| Tên | Link |
|---|---|
| ACL rank | https://portal.core.edu.au/conf-ranks/196/ |
| ICLR rank | https://portal.core.edu.au/conf-ranks/2273/ |
| NeurIPS rank | https://portal.core.edu.au/conf-ranks/98/ |
| NAACL rank | https://portal.core.edu.au/conf-ranks/?by=acronym&search=NAACL |
| EMNLP rank | https://portal.core.edu.au/conf-ranks/?by=acronym&search=EMNLP |
| TACL Q1 | https://www.scimagojr.com/journalsearch.php?clean=0&q=21101049047&tip=sid |
| Computational Linguistics Q1 | https://www.scimagojr.com/journalsearch.php?q=26801&tip=sid |
| TACL indexing | https://direct.mit.edu/tacl/pages/abstracting-indexing |

### 17.3 Nguồn kỹ thuật phụ trợ

| Tên | Link |
|---|---|
| ELI5 official repo | https://github.com/facebookresearch/ELI5 |
| ELI5 dataset explorer | https://facebookresearch.github.io/ELI5/ |
| Qwen2.5-VL-3B-Instruct model card | https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct |

