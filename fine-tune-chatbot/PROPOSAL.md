# Đề xuất: Kế hoạch Fine-tune tiếng Anh cho `fine-tune-chatbot`

## 1. Mục tiêu

Tài liệu này đề xuất một hướng fine-tune mới cho chatbot trong thư mục `fine-tune-chatbot` với các quyết định chính sau:

- Giữ nguyên bộ dataset hiện tại của dự án và xem đây là **nguồn dữ liệu domain chính**.
- Chuyển chatbot sang **full tiếng Anh**.
- Dùng **`Qwen/Qwen2.5-7B-Instruct`** làm base model.
- Dùng **ELI5** như một **dataset phụ trợ đã lọc**, không dùng như nguồn dữ liệu duy nhất hay nguồn dữ liệu chi phối.
- Đánh giá mô hình bằng bộ benchmark bám sát bài toán thật hơn: **trợ giảng AI/ML/NLP/CV**, không chỉ benchmark instruction-following chung chung.

Luận điểm chính của proposal này là:

> ELI5 hữu ích để dạy mô hình cách trả lời giải thích dài, mạch lạc bằng tiếng Anh, nhưng không phù hợp để thay thế dataset domain hiện có của dự án. Với bài toán này, ELI5 nên được dùng như một nguồn phụ trợ để cải thiện phong cách giải thích.

---

## 2. Vì sao hướng hiện tại chưa đủ thuyết phục

Từ các tài liệu hiện có trong thư mục `fine-tune-chatbot`, pipeline cũ đang biện minh external data chủ yếu theo hướng “bổ sung thêm instruction data”. Cách lập luận đó chưa đủ mạnh cho bài toán này, vì chatbot đích không phải trợ lý tổng quát mà gần với một **domain tutor** cho AI/ML/NLP/CV.

Các điểm yếu chính của hướng cũ:

- External data còn quá generic so với domain đích.
- Mục tiêu huấn luyện chưa tách bạch rõ:
  - tri thức domain,
  - phong cách giải thích,
  - năng lực dùng để benchmark.
- Bộ benchmark còn rộng và chưa đủ sát với bài toán trợ giảng AI/ML/NLP/CV.

Muốn proposal thuyết phục hơn, cần làm rõ:

1. dataset hiện tại của dự án dạy mô hình điều gì,
2. ELI5 bổ sung được điều gì mà dataset hiện tại chưa mạnh,
3. ELI5 không nên bị kỳ vọng làm được điều gì,
4. đánh giá thành công của mô hình bằng tiêu chí nào.

---

## 3. Mô hình nền khuyến nghị

Đề xuất dùng **`Qwen/Qwen2.5-7B-Instruct`**.

Lý do mô hình này phù hợp:

- Đây là một open 7B instruct model mạnh, có năng lực tốt về **reasoning, coding, structured output và long-context generation**.
- Model card hiện tại trên Hugging Face ghi rõ license **Apache-2.0** và hỗ trợ ngữ cảnh dài tới **128K**.
- Vì proposal này định hướng chatbot sang **full English**, `Qwen2.5-7B-Instruct` hợp lý hơn so với cách trộn nhiều nguồn dữ liệu nghiêng về tiếng Việt.

Proposal này giả định **fine-tune text-only**. Nếu sau này dự án cần hỗ trợ mạnh cho ảnh, slide, sơ đồ CV, thì đó nên là một phase multimodal riêng, không nên trộn vào quyết định dataset ở giai đoạn này.

---

## 4. Quan điểm về ELI5

## Kết luận ngắn

Có thể dùng ELI5, nhưng:

- **không dùng raw**,
- **không dùng toàn bộ**,
- **không dùng làm corpus chính**.

## Vì sao ELI5 hấp dẫn

ELI5 được giới thiệu bởi Fan et al. như một dataset long-form question answering với khoảng **270K thread Reddit**, tập trung vào kiểu trả lời mang tính giải thích.

Điều này quan trọng với dự án vì chatbot của bạn không chỉ cần trả lời ngắn, mà còn cần:

- trả lời được các câu hỏi kiểu “why” và “how”,
- tạo câu trả lời dài theo đoạn,
- giữ giọng điệu mang tính giảng giải,
- diễn đạt ý kỹ thuật bằng tiếng Anh tự nhiên hơn.

Đây chính là phần mà ELI5 mạnh hơn một bộ MCQ domain nhỏ.

## Vì sao ELI5 không đủ nếu dùng một mình

ELI5 vẫn là một lựa chọn sai nếu dùng thiếu kiểm soát:

- Đây là **general-domain**, không phải dataset chuyên cho AI/ML/NLP/CV.
- Dữ liệu đến từ **Reddit**, nên phong cách và chất lượng factual không đồng đều.
- Nó được tạo cho bài toán **long-form QA**, không phải tutor bám sát course material.
- Các công trình sau này đã chỉ ra những vấn đề quan trọng của benchmark ELI5, như **train/validation overlap** và metric tự động yếu cho LFQA.

Do đó, ELI5 nên được dùng để dạy mô hình:

- độ dài lời giải thích,
- cách tổ chức câu trả lời,
- phong cách “giải thích như người dạy”,
- độ trôi chảy của long-form QA bằng tiếng Anh.

ELI5 **không nên** bị xem là nguồn tri thức chính cho chatbot AI/ML/NLP/CV.

---

## 5. Vì sao ELI5 vẫn hợp lý cho dự án này

ELI5 vẫn đáng dùng ở đây vì bốn lý do cụ thể.

### 5.1 ELI5 bổ sung cho dataset hiện tại thay vì cạnh tranh với nó

Dataset hiện tại của dự án đã mang tín hiệu domain quan trọng nhất. ELI5 đóng góp một loại năng lực khác:

- dataset hiện tại dạy mô hình **nói cái gì** trong domain,
- ELI5 dạy mô hình **giải thích dài bằng tiếng Anh như thế nào**.

Cách phân vai này rõ ràng và dễ bảo vệ.

### 5.2 ELI5 phù hợp với định hướng chuyển sang full English

Nếu dự án chuyển từ dữ liệu trộn ngôn ngữ sang full English, ELI5 hợp lý hơn nhiều so với các bộ translated instruction data generic, vì:

- bản chất nó là tiếng Anh,
- thiên về giải thích,
- chứa nhiều câu hỏi “why/how” hơn là các cặp instruction-response ngắn.

### 5.3 ELI5 có nền tảng nghiên cứu đủ mạnh

ELI5 không phải một bộ dữ liệu ngẫu nhiên trên Hugging Face. Nó gắn với nhiều công trình long-form QA có uy tín và các benchmark lớn sau này.

ELI5 xuất hiện trong:

- **Fan et al., ACL 2019**: bài báo gốc giới thiệu ELI5.
- **Petroni et al., NAACL 2021 (KILT)**: ELI5 được đưa vào benchmark KILT cho các tác vụ knowledge-intensive.
- **Krishna et al., NAACL 2021**: phân tích phê bình, chỉ ra ELI5 quan trọng nhưng phải đánh giá cẩn thận.
- **Su et al., Findings of ACL 2022**: dùng ELI5 làm benchmark chính cho faithful long-form QA.
- **WebGPT (OpenAI, 2021)**: huấn luyện và đánh giá trên các câu hỏi mở kiểu ELI5.

Đây là chuỗi citation đủ mạnh để biện minh với giảng viên rằng việc chọn ELI5 có cơ sở học thuật.

### 5.4 ELI5 nhắm đúng kiểu lỗi quan trọng của tutor chatbot

Với một chatbot trợ giảng, nhiều lỗi không phải là sai fact đơn thuần mà là lỗi giải thích:

- trả lời quá ngắn,
- giải thích quá nông,
- câu trả lời rời rạc,
- không có tính sư phạm,
- không giữ được mạch logic qua cả đoạn văn.

ELI5 đánh trực tiếp vào nhóm vấn đề này.

---

## 6. Lưu ý quan trọng: dùng ELI5 đã lọc, không dùng full ELI5

Khuyến nghị của tôi là tạo một **ELI5-filtered subset** dành riêng cho repo này.

### 6.1 Luật lọc cơ bản

Chỉ giữ các sample thỏa phần lớn các điều kiện sau:

- Câu hỏi mang tính giải thích: bắt đầu bằng hoặc ngầm mang nghĩa `why`, `how`, `what happens`, `what is the difference`, `how does`.
- Câu trả lời có độ dài trung bình đến dài, ví dụ `120-450` từ.
- Câu trả lời mạch lạc, thiên về giải thích, không quá nhiều joke hoặc chat noise.
- Chủ đề phải ít nhất gần với khoa học, toán, tính toán, logic, dữ liệu, ngôn ngữ, tối ưu, xác suất hoặc kỹ thuật.
- Loại bỏ các nhóm chủ đề như celebrity trivia, sports trivia, politics, entertainment và các nội dung không liên quan.

### 6.2 Bộ lọc bám theo bài toán của dự án

Nên xây bộ lọc topic relevance theo keyword hoặc semantic similarity quanh các nhóm:

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

### 6.3 Bộ lọc chất lượng dữ liệu

Nên loại bỏ các sample có dấu hiệu:

- quá thiên về ý kiến chủ quan hoặc suy đoán,
- nặng first-person anecdote,
- có sarcasm hoặc Reddit meta-discussion,
- answer không khớp question,
- duplicate hoặc near-duplicate.

### 6.4 Vai trò cuối cùng của ELI5 trong pipeline

Sau khi lọc, ELI5 nên trở thành một **nguồn phụ trợ để dạy explanation behavior**, không phải nguồn dữ liệu chi phối.

---

## 7. Tỷ lệ trộn dữ liệu đề xuất

Tỷ lệ trộn dữ liệu cho vòng đầu:

- **65-75%**: dataset hiện tại của dự án, giữ nguyên
- **20-30%**: filtered ELI5 subset
- **5-10%**: dữ liệu cân bằng format / instruction nếu cần

Tôi **không khuyến nghị** vượt quá ~30% ELI5 ở v1, vì khi đó độ lệch domain sẽ bắt đầu kéo hành vi mô hình đi xa bài toán thật.

### Vì sao tỷ lệ này hợp lý

- Dataset hiện tại vẫn là neo chính cho tri thức AI/ML/NLP/CV.
- ELI5 bổ sung phong cách giải thích bằng tiếng Anh.
- Mô hình vẫn giữ trọng tâm domain thay vì biến thành một general explainer.

Nếu sau này thấy mô hình giải thích chưa tốt, có thể tăng ELI5 nhẹ.  
Nếu thấy mô hình bị domain drift, nên giảm ELI5 trước khi thay đổi các yếu tố khác.

---

## 8. Preview vài dòng dữ liệu ELI5

Dưới đây là các preview ngắn, đã **lược bớt**, để minh họa kiểu dữ liệu ELI5.

### Ví dụ A

- Question: `why chemical weapons are considered more indiscriminate than conventional weapons`
- Kiểu answer: giải thích nhiều câu về độ lan rộng, độ tồn dư và collateral damage

### Ví dụ B

- Question: `in football, why waste the first two plays with a rush up the middle`
- Kiểu answer: giải thích reasoning của chiến thuật, không chỉ trả lời 1 dòng

### Ví dụ C

- Trong bản KILT mirror, sample có dạng một prompt mở cùng một hoặc nhiều answer, kèm provenance
- Giá trị với dự án: có thể convert thành instruction-style QA, nhưng vẫn phải lọc theo domain

Các preview này cho thấy lợi ích chính:

- ELI5 dạy **cấu trúc giải thích**,
- nhưng phân bố chủ đề thô của nó quá rộng để đưa thẳng vào fine-tune.

---

## 9. ELI5 đã được dùng trong những paper nào

ELI5 có độ tin cậy vì đã xuất hiện hoặc được phân tích trong nhiều bối cảnh nghiên cứu quan trọng:

1. **ELI5: Long Form Question Answering**  
   Fan et al., ACL 2019  
   Bài báo gốc giới thiệu ELI5 là dataset long-form QA quy mô lớn.

2. **KILT: a Benchmark for Knowledge Intensive Language Tasks**  
   Petroni et al., NAACL 2021  
   Đưa ELI5 vào benchmark lớn có grounding trên cùng một Wikipedia snapshot.

3. **Hurdles to Progress in Long-form Question Answering**  
   Krishna et al., NAACL 2021  
   Chỉ ra các vấn đề quan trọng khi dùng ELI5 và nhấn mạnh không nên đánh giá ngây thơ.

4. **Read before Generate! Faithful Long Form Question Answering with Machine Reading**  
   Su et al., Findings of ACL 2022  
   Dùng ELI5 như một benchmark chính cho long-form QA có grounding tốt hơn.

5. **WebGPT: Improving the factual accuracy of language models through web browsing**  
   OpenAI, December 2021  
   Dùng các câu hỏi kiểu ELI5 để huấn luyện và đánh giá hệ thống.

Điểm quan trọng khi trình bày với giảng viên là:

- ELI5 là dataset có tiếng,
- nhưng các paper mạnh cũng chỉ ra giới hạn của nó,
- vì vậy phải dùng ELI5 có kiểm soát, kèm benchmark cẩn thận.

Lập luận đó mạnh hơn nhiều so với việc chỉ nói “ELI5 lớn nên train tốt”.

---

## 10. Bộ benchmark phù hợp với bài toán của dự án

Bài toán thật của chatbot là: **hỏi đáp và giải thích về AI/ML/NLP/CV**.  
Vì vậy benchmark phải đo đúng việc đó.

## Tier A: Benchmark chính của repo

Dùng **held-out split từ chính dataset hiện tại của dự án** làm shipping gate quan trọng nhất.

Đây là benchmark quan trọng nhất vì nó đo trực tiếp đúng hành vi chatbot cần có trong dự án.

Các chỉ số nên có:

- độ chính xác MCQ trên tập câu hỏi course-held-out,
- chất lượng câu trả lời giải thích trên các câu hỏi mở chuyển đổi từ tập held-out,
- độ chính xác của thuật ngữ AI/ML/NLP/CV,
- khả năng điều chỉnh mức độ ngắn/dài của câu trả lời.

Chính sách split nên là:

- group theo lecture / topic / source unit,
- train/val/test phải tách nhau theo topic,
- không để paraphrase của cùng một câu hỏi xuất hiện khác split.

## Tier B: Benchmark học thuật external nhưng sát domain hơn

### 10.1 MMLU theo subject subset

Nên dùng **MMLU**, nhưng **không dùng global score** làm câu chuyện chính.  
Chỉ lấy các subject gần bài toán:

- `machine_learning`
- `college_computer_science`
- `college_mathematics`
- `high_school_statistics`
- `abstract_algebra` hoặc `formal_logic` như stress test phụ

Lý do:

- Đây là benchmark quen thuộc, dễ trao đổi học thuật.
- Subject slicing khiến nó sát bài toán hơn nhiều so với một điểm MMLU tổng.

### 10.2 MMLU-Pro

Nên dùng **MMLU-Pro** như benchmark khó hơn ở tầng thứ hai.

Lý do:

- Đây là benchmark được đề xuất để robust hơn và khó hơn MMLU.
- Hữu ích để kiểm tra mô hình fine-tune không chỉ học các pattern dễ.

### 10.3 TheoremQA

Nên dùng **TheoremQA**, đặc biệt các phần **EE&CS, Math, Physics**.

Lý do phù hợp:

- Nó gần technical reasoning hơn các benchmark chat thông thường.
- Dataset này được curate bởi domain experts.
- Nó phù hợp với một tutor cần giải thích các nền tảng toán cho ML.

Đây là benchmark rất hợp với loại tri thức nằm gần CS224n / CS231n / CS230.

## Tier C: Benchmark cho phong cách giải thích

Dùng một **dev/test slice riêng của filtered ELI5** chỉ như **style-and-explanation benchmark**.

Không dùng phần này làm tiêu chí chính để ship model.

Phần này chỉ để đo:

- độ dài câu trả lời,
- độ mạch lạc,
- cấu trúc giải thích,
- giọng điệu giải thích bằng tiếng Anh.

Mục đích là kiểm tra xem ELI5 có thật sự giúp phần behavior mà ta muốn cải thiện hay không.

---

## 11. Những benchmark không nên dùng làm tiêu chí chính

Tôi không khuyến nghị dùng các benchmark sau làm câu chuyện chính cho dự án:

- **global MMLU score**  
  Quá rộng và không đủ sát bài toán trợ giảng AI/ML/NLP/CV.

- **GSM8K đơn lẻ**  
  Hữu ích cho arithmetic reasoning nhưng quá hẹp so với chatbot mục tiêu.

- **generic chat benchmark**  
  Không trả lời được câu hỏi liệu mô hình có giải thích tốt transformer, backpropagation, attention, CNN hay không.

- **raw ELI5 score làm shipping gate**  
  Cách này dễ đánh giá quá cao độ trôi chảy long-form và đánh giá quá thấp độ đúng domain.

---

## 12. Giao thức benchmark cụ thể

### 12.1 Trước khi fine-tune

Đánh giá base `Qwen/Qwen2.5-7B-Instruct` trên:

- internal held-out domain set,
- MMLU selected subjects,
- MMLU-Pro STEM slice hoặc full,
- TheoremQA selected categories,
- filtered ELI5 dev slice.

### 12.2 Sau khi fine-tune

Chạy lại đúng bộ đánh giá đó và so sánh delta.

### 12.3 Tiêu chí thành công

Các ngưỡng thực dụng nên là:

- Internal domain benchmark: **phải tăng**
- MMLU selected subjects: **không được giảm đáng kể**
- TheoremQA: **tăng nhẹ hoặc ít nhất không tụt mạnh**
- Filtered ELI5 explanation benchmark: **phải cải thiện rõ về chất lượng giải thích**

Nếu internal domain tăng nhưng MMLU-style score giảm nhẹ thì vẫn có thể chấp nhận.  
Nếu ELI5-style fluency tăng nhưng độ đúng AI/ML/NLP/CV giảm thì run đó nên bị loại.

---

## 13. Kế hoạch triển khai thực tế trong repo này

### Phase 1

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Phương pháp: QLoRA / LoRA
- Ngôn ngữ: English only
- Dữ liệu:
  - dataset hiện tại của dự án, giữ nguyên
  - filtered ELI5 subset

### Phase 2

Tạo ba file validation:

- `domain_eval.jsonl`
- `eli5_style_eval.jsonl`
- `external_reasoning_eval.jsonl`

### Phase 3

Theo dõi ablation:

- run A: chỉ dataset của dự án
- run B: dataset dự án + 10% ELI5
- run C: dataset dự án + 20% ELI5
- run D: dataset dự án + 30% ELI5

Điểm này rất quan trọng vì nó cho phép chứng minh ELI5 có thực sự giúp hay không, thay vì giả định nó giúp.

---

## 14. Khuyến nghị cuối cùng

Proposal mạnh nhất cho dự án này là:

1. Giữ dataset hiện tại làm nguồn domain chính.
2. Chuyển sang `Qwen/Qwen2.5-7B-Instruct`.
3. Chuyển chatbot sang full English.
4. Dùng **filtered ELI5** như một dataset phụ trợ cho explanation style.
5. Benchmark chủ yếu bằng:
   - held-out internal AI/ML/NLP/CV data,
   - MMLU selected subjects,
   - MMLU-Pro,
   - TheoremQA,
   - filtered ELI5 dev chỉ để đo explanation style.

Nếu trình bày ELI5 theo hướng này, lập luận sẽ mạnh hơn nhiều:

- ELI5 không thay dataset domain của bạn,
- ELI5 lấp đúng khoảng trống về cách giải thích bằng tiếng Anh,
- ELI5 có hậu thuẫn từ các paper mạnh,
- các giới hạn của ELI5 đã được thừa nhận và kiểm soát,
- benchmark thì bám sát đúng bài toán chatbot trợ giảng.

Đây là một kế hoạch fine-tune có thể bảo vệ được và có thể triển khai ngay trong repo này.

---

## 15. Nguồn tham khảo

Các nguồn được dùng để xây dựng proposal này:

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

Ghi chú triển khai:

- Dataset card hiện tại của `facebook/kilt_tasks` trên Hugging Face ghi `mit`.
- Repository gốc của ELI5 cũng nêu rõ dữ liệu processed Reddit/CommonCrawl có ràng buộc về hosting.
- Khi triển khai trong dự án, cần pin đúng nguồn dataset được tải và ghi lại trong training manifest.
