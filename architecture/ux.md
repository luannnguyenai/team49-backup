# UX Flowcharts — AI Tutor Overlay (VinSchool)

Tài liệu này mô tả trải nghiệm người dùng qua **6 sơ đồ Mermaid**:

1. Tổng quan luồng UX
2. F1 — Giải thích khái niệm: 4 paths
3. F2 — Gợi ý chủ động: 4 paths
4. F3 — Hội thoại follow-up: 4 paths
5. Luồng phát hiện ngữ cảnh (Context Detection Pipeline)
6. Vòng lặp phản hồi & Data Flywheel

---

## 1. Tổng quan luồng UX

Luồng chính từ lúc sinh viên mở bài giảng đến khi kết thúc tương tác với AI.

```mermaid
graph TD
    START(["🎓 Sinh viên mở bài giảng\ntrên LMS/Video/Slide"])
    CTX["Hệ thống thu ngữ cảnh ngầm\nSlide hiện tại · Timestamp video · Transcript"]
    DETECT{"Phát hiện\ntương tác?"}

    HOVER["Hover / Pause ≥ 3s\ntrên thuật ngữ"]
    CLICK["Bôi đen text\nhoặc nhấn 'Hỏi AI'"]
    CONTINUE(["▶ Tiếp tục học\nbình thường"])

    PROACTIVE["F2: Gợi ý chủ động\nhiện chip nhỏ"]
    EXPLICIT["F1: Giải thích\ntheo ngữ cảnh"]

    OVERLAY(["💬 Overlay AI mở"])
    RESPONSE["AI trả lời\n+ Badge nguồn tham khảo"]

    EVAL{"Sinh viên\nđánh giá"}
    UNDERSTOOD(["✅ Đã hiểu\nOverlay đóng\nGhi signal +1"])
    FOLLOWUP["F3: Hội thoại\nfollow-up"]
    WRONG["Báo sai\nGhi correction log"]

    START --> CTX
    CTX --> DETECT
    DETECT -- "Passive" --> HOVER
    DETECT -- "Active" --> CLICK
    DETECT -- "Không có" --> CONTINUE

    HOVER --> PROACTIVE
    CLICK --> EXPLICIT
    PROACTIVE --> OVERLAY
    EXPLICIT --> OVERLAY

    OVERLAY --> RESPONSE
    RESPONSE --> EVAL
    EVAL -- "Đã hiểu" --> UNDERSTOOD
    EVAL -- "Hỏi tiếp" --> FOLLOWUP
    EVAL -- "Sai rồi" --> WRONG
    FOLLOWUP --> RESPONSE
    WRONG --> CONTINUE
    UNDERSTOOD --> CONTINUE

    classDef happy fill:#d4edda,stroke:#28a745,color:#155724
    classDef fail fill:#f8d7da,stroke:#dc3545,color:#721c24
    classDef warn fill:#fff3cd,stroke:#ffc107,color:#856404
    classDef neutral fill:#e2e3e5,stroke:#6c757d,color:#383d41

    class UNDERSTOOD happy
    class WRONG fail
    class PROACTIVE warn
    class CONTINUE neutral
```

---

## 2. F1 — Giải thích khái niệm theo ngữ cảnh (4 Paths)

Sinh viên chủ động hỏi → hệ thống phân nhánh theo độ tự tin và tính đúng đắn của AI.

```mermaid
graph TD
    TRIGGER(["Trigger: Sinh viên bôi đen\nhoặc nhấn 'Hỏi AI'"])
    OCR["Thu OCR slide hiện tại\n+ Timestamp video\n+ Câu hỏi sinh viên"]
    RAG{"Tìm thấy trong\nRAG index?"}

    %% Happy path
    FOUND["AI phân tích context\nvà tạo câu trả lời"]
    CONF{"AI confidence\n≥ threshold?"}
    ANSWER_HIGH["Trả lời đầy đủ\n+ Badge nguồn xanh\n'Nguồn: Slide 7'"]
    HAPPY_END(["✅ Happy Path\nSinh viên nhấn 'Đã hiểu'\nOverlay đóng · Signal +1"])

    %% Low-confidence path
    ANSWER_LOW["Trả lời kèm\nBanner vàng cảnh báo:\n'Dựa trên kiến thức chung\n— hãy xác minh lại'"]
    LOW_CHOICE{"Sinh viên\nchọn gì?"}
    EXT_SRC(["🔗 Xem nguồn ngoài\nGoogle Scholar / Wikipedia"])
    CLOSE_LOW(["✖ Đóng overlay\ntiếp tục tự nghiên cứu"])

    %% Failure path
    NOT_FOUND["AI trả lời:\n'Không tìm thấy thông tin\ntrong tài liệu hiện tại'"]
    FAIL_CHOICE{"Sinh viên\nchọn gì?"}
    ASK_TEACHER(["📩 Đặt câu hỏi\ncho giảng viên"])
    SELF_SEARCH(["🔍 Tự tìm\nbên ngoài"])

    %% Correction path
    SILENT_FAIL["⚠ Silent Failure\nAI trả lời SAI\nnhưng trông đúng"]
    REPORT["Sinh viên nhấn\n'Báo sai'"]
    FORM["Form nhỏ xuất hiện:\n'Câu trả lời đúng là gì?'"]
    LOG(["📝 Ghi Correction Log\n{câu hỏi, context,\ncâu trả lời sai,\ncâu trả lời đúng}"])

    TRIGGER --> OCR
    OCR --> RAG

    RAG -- "Có" --> FOUND
    FOUND --> CONF
    CONF -- "Cao ≥ 80%" --> ANSWER_HIGH
    CONF -- "Thấp < 80%" --> ANSWER_LOW
    ANSWER_HIGH --> HAPPY_END

    ANSWER_LOW --> LOW_CHOICE
    LOW_CHOICE -- "Xem nguồn ngoài" --> EXT_SRC
    LOW_CHOICE -- "Đóng" --> CLOSE_LOW

    RAG -- "Không" --> NOT_FOUND
    NOT_FOUND --> FAIL_CHOICE
    FAIL_CHOICE -- "Hỏi giảng viên" --> ASK_TEACHER
    FAIL_CHOICE -- "Tự tìm" --> SELF_SEARCH

    ANSWER_HIGH -. "Sau khi đọc kỹ\nphát hiện sai" .-> SILENT_FAIL
    SILENT_FAIL --> REPORT
    REPORT --> FORM
    FORM --> LOG

    classDef happy fill:#d4edda,stroke:#28a745,color:#155724
    classDef low fill:#fff3cd,stroke:#ffc107,color:#856404
    classDef fail fill:#f8d7da,stroke:#dc3545,color:#721c24
    classDef correct fill:#cce5ff,stroke:#004085,color:#004085
    classDef process fill:#f8f9fa,stroke:#adb5bd,color:#343a40

    class HAPPY_END happy
    class ANSWER_LOW,LOW_CHOICE,EXT_SRC,CLOSE_LOW low
    class NOT_FOUND,FAIL_CHOICE,ASK_TEACHER,SELF_SEARCH,SILENT_FAIL fail
    class REPORT,FORM,LOG correct
    class TRIGGER,OCR,RAG,FOUND,CONF,ANSWER_HIGH process
```

---

## 3. F2 — Gợi ý chủ động (Proactive Suggestion) — 4 Paths

AI chủ động gợi ý khi phát hiện sinh viên có thể đang gặp khó khăn.

```mermaid
graph TD
    WATCH(["👁 Hệ thống theo dõi\nhành vi ngầm"])

    PAUSE_DET{"Phát hiện\nhành vi?"}
    HOVER_EV["Hover ≥ 3s trên\nthuật ngữ được gạch chân"]
    PAUSE_EV["Pause video\n≥ 3 giây"]

    CTX_CHECK{"Có đủ context\nđể gợi ý?"}

    %% Happy path
    CHIP_SHOW["Hiện chip gợi ý nhỏ\n(góc phải màn hình):\n'Bạn muốn hiểu [Khái niệm X] không?'"]
    USER_RES{"Sinh viên\nphản hồi?"}
    ACCEPT(["✅ Happy Path\nSinh viên nhấn 'Có'\n→ Overlay F1 mở"])
    IGNORE["Không phản hồi\ntrong 4 giây"]
    CHIP_FADE(["🔅 Chip tự mờ đi\ntiếp tục học"])

    %% Low-confidence path
    NO_CTX(["🔇 Low-confidence Path\nKhông đủ context\n→ Không hiện chip\n'Thà im còn hơn sai'"])

    %% Failure path
    WRONG_TERM["⚠ Failure Path\nChip gợi ý sai\nkhái niệm / không liên quan"]
    DISMISS["Sinh viên nhấn X\nhoặc dismiss chip"]
    LOG_DISMISS["Ghi dismiss signal\ncho context này"]
    REDUCE(["📉 Giảm probability\ngợi ý cho pattern tương tự"])

    %% Correction path
    ASK_OTHER(["✏ Correction Path\nSinh viên nhấn\n'Hỏi điều khác'\n→ Gõ câu hỏi tự do\nvào F1"])

    RATE_LIMIT{"Đã gợi ý\n≥ 2 lần\ntrong 10 phút?"}
    COOLDOWN(["⏸ Vào cooldown\nKhông gợi ý thêm\ncho phiên này"])

    WATCH --> PAUSE_DET
    PAUSE_DET -- "Có" --> HOVER_EV & PAUSE_EV
    PAUSE_DET -- "Không" --> WATCH

    HOVER_EV & PAUSE_EV --> RATE_LIMIT
    RATE_LIMIT -- "Chưa" --> CTX_CHECK
    RATE_LIMIT -- "Rồi" --> COOLDOWN

    CTX_CHECK -- "Đủ" --> CHIP_SHOW
    CTX_CHECK -- "Không đủ" --> NO_CTX

    CHIP_SHOW --> USER_RES
    USER_RES -- "Nhấn Có" --> ACCEPT
    USER_RES -- "Bỏ qua" --> IGNORE
    USER_RES -- "Nhấn X" --> DISMISS
    USER_RES -- "Hỏi điều khác" --> ASK_OTHER
    IGNORE --> CHIP_FADE

    DISMISS --> LOG_DISMISS
    LOG_DISMISS --> REDUCE

    classDef happy fill:#d4edda,stroke:#28a745,color:#155724
    classDef low fill:#fff3cd,stroke:#ffc107,color:#856404
    classDef fail fill:#f8d7da,stroke:#dc3545,color:#721c24
    classDef correct fill:#cce5ff,stroke:#004085,color:#004085
    classDef neutral fill:#e2e3e5,stroke:#6c757d,color:#383d41

    class ACCEPT happy
    class NO_CTX,COOLDOWN low
    class WRONG_TERM,DISMISS,LOG_DISMISS,REDUCE fail
    class ASK_OTHER correct
    class CHIP_FADE,IGNORE neutral
```

---

## 4. F3 — Hội thoại Follow-up — 4 Paths

Sau câu trả lời đầu tiên, sinh viên tiếp tục đào sâu trong cùng overlay.

```mermaid
graph TD
    FIRST_ANS(["💬 AI vừa trả lời\ncâu hỏi đầu tiên"])

    CHOICE{"Sinh viên\nchọn gì?"}
    DONE(["✅ Đã hiểu\nKết thúc · Đóng overlay"])
    FOLLOWUP_Q["Nhấn 'Hỏi tiếp'\nhoặc gõ câu hỏi mới"]

    COUNT{"Số lượt\nfollow-up?"}

    %% Happy path
    MAINTAIN["AI duy trì context\nhội thoại + slide hiện tại"]
    DEEPER["AI mở rộng giải thích\ndựa trên Q&A trước"]
    HAPPY_END(["✅ Happy Path\nSinh viên đào sâu thành công\nNhấn 'Đã hiểu' sau 2-3 lượt"])

    %% Low-confidence path
    ESCALATE["⚠ Low-confidence Path\nAI gợi ý thoát loop:\n'Bạn muốn xem lại\nphần này trong video không?'"]
    LINK_VID(["🎬 Link timestamp video\ntương ứng với khái niệm"])
    CONTINUE_Q["Sinh viên muốn\ntiếp tục hỏi AI"]

    %% Failure path
    LOST_CTX["🔴 Failure Path\nAI mất mạch context\nTrả lời không liên quan\nhoặc lặp lại"]
    USER_NOTICE["Sinh viên nhận ra\ncâu trả lời lạc đề"]
    RESET_BTN["Nhấn 'Hỏi lại từ đầu'"]

    %% Correction path
    RESET_CTX["Correction Path\nXoá conversation history\nGiữ nguyên slide context"]
    REPHRASE(["✏ Sinh viên gõ lại\ncâu hỏi rõ hơn\n→ Quay về F1"])

    FIRST_ANS --> CHOICE
    CHOICE -- "Đã hiểu" --> DONE
    CHOICE -- "Hỏi tiếp" --> FOLLOWUP_Q

    FOLLOWUP_Q --> COUNT
    COUNT -- "< 3 lượt" --> MAINTAIN
    COUNT -- "≥ 3 lượt\ncùng khái niệm" --> ESCALATE

    MAINTAIN --> DEEPER
    DEEPER --> HAPPY_END

    ESCALATE --> LINK_VID
    ESCALATE --> CONTINUE_Q
    CONTINUE_Q --> FOLLOWUP_Q

    DEEPER -. "AI drift /\nconfuse context" .-> LOST_CTX
    LOST_CTX --> USER_NOTICE
    USER_NOTICE --> RESET_BTN
    RESET_BTN --> RESET_CTX
    RESET_CTX --> REPHRASE

    classDef happy fill:#d4edda,stroke:#28a745,color:#155724
    classDef low fill:#fff3cd,stroke:#ffc107,color:#856404
    classDef fail fill:#f8d7da,stroke:#dc3545,color:#721c24
    classDef correct fill:#cce5ff,stroke:#004085,color:#004085

    class DONE,HAPPY_END happy
    class ESCALATE,LINK_VID,CONTINUE_Q low
    class LOST_CTX,USER_NOTICE,RESET_BTN fail
    class RESET_CTX,REPHRASE correct
```

---

## 5. Luồng phát hiện ngữ cảnh (Context Detection Pipeline)

Pipeline kỹ thuật xảy ra trong nền mỗi khi sinh viên tương tác — trước khi AI nhận được bất kỳ câu hỏi nào.

```mermaid
graph LR
    INPUT(["📄 Input\nSinh viên\ntương tác"])

    subgraph DETECT ["Phát hiện loại nội dung"]
        TYPE{"Loại\nnội dung?"}
        SLIDE_PATH["Slide PDF"]
        VIDEO_PATH["Video bài giảng"]
        TEXT_PATH["Trang text LMS"]
    end

    subgraph EXTRACT ["Trích xuất ngữ cảnh"]
        OCR["OCR trang hiện tại\n(Tesseract / Google Vision)"]
        TRANSCRIPT{"Có\ntranscript?"}
        TS_CHUNK["Chunk transcript\ntheo timestamp ±30s"]
        NO_TS["⚠ Cảnh báo:\nKhông có transcript\nChất lượng AI giảm"]
        DOM_TXT["Extract DOM text\ntừ trang LMS"]
    end

    subgraph RAG_LAYER ["RAG & Context injection"]
        INDEX["RAG Index\n(tài liệu course)"]
        SEARCH["Semantic search\ntrên context vừa trích"]
        INJECT["Inject context\nvào prompt:\nContext + Câu hỏi"]
    end

    subgraph AI_CALL ["AI Inference"]
        MODEL["Gemini 2.0 Flash\nGPT-4o Vision"]
        RESP["Response\n+ Confidence score\n+ Source citation"]
    end

    LATENCY(["⏱ Tổng latency\nmục tiêu < 2s"])

    INPUT --> TYPE
    TYPE -- "Slide" --> SLIDE_PATH --> OCR
    TYPE -- "Video" --> VIDEO_PATH --> TRANSCRIPT
    TYPE -- "Text" --> TEXT_PATH --> DOM_TXT

    TRANSCRIPT -- "Có" --> TS_CHUNK
    TRANSCRIPT -- "Không" --> NO_TS

    OCR --> SEARCH
    TS_CHUNK --> SEARCH
    DOM_TXT --> SEARCH
    NO_TS --> SEARCH

    INDEX --> SEARCH
    SEARCH --> INJECT
    INJECT --> MODEL
    MODEL --> RESP
    RESP --> LATENCY

    classDef warn fill:#fff3cd,stroke:#ffc107,color:#856404
    classDef process fill:#e8f4f8,stroke:#17a2b8,color:#0c5460

    class NO_TS warn
    class OCR,TS_CHUNK,DOM_TXT,SEARCH,INJECT,MODEL process
```

---

## 6. Vòng lặp phản hồi & Data Flywheel

Mỗi tương tác của sinh viên tạo ra signal → cải thiện chất lượng AI theo thời gian.

```mermaid
flowchart TD
    INTERACT(["🎓 Sinh viên\ntương tác với AI"])

    subgraph SIGNALS ["Thu thập Learning Signals"]
        S1["✅ Đã hiểu\n→ +1 positive signal\ncho context này"]
        S2["❓ Hỏi tiếp\n(cùng khái niệm)\n→ Câu trả lời chưa đủ"]
        S3["❌ Báo sai\n→ Correction log\n{câu hỏi, sai, đúng}"]
        S4["✖ Dismiss chip\n→ Negative signal\ncho proactive pattern"]
        S5["⏱ Thời gian ở lại\nLMS sau khi hỏi\n→ Engagement signal"]
    end

    subgraph ANALYSIS ["Phân tích định kỳ (Weekly)"]
        METRIC1["Tỷ lệ Đã hiểu\n≥ 75% → OK\n< 50% → Alert"]
        METRIC2["Tỷ lệ hallucination\n≤ 5% → OK\n> 15% → Stop & Review"]
        METRIC3["Latency P95\n≤ 2s → OK\n> 4s → Optimize"]
    end

    subgraph IMPROVE ["Cải thiện hệ thống"]
        RAG_UPDATE["Cập nhật RAG Index\ntừ correction log"]
        PROMPT_TUNE["Điều chỉnh system prompt\ntheo pattern lỗi thường gặp"]
        PROACT_TUNE["Điều chỉnh threshold\ngợi ý chủ động\ntheo dismiss rate"]
        SLIDE_UPDATE["Giảng viên bổ sung\ntranscript / tài liệu mới"]
    end

    FLYWHEEL(["🔄 Data Flywheel\nAI biết nội dung VinSchool\nngày càng sâu hơn\nModel ngoài không có"])

    INTERACT --> S1 & S2 & S3 & S4 & S5

    S1 & S2 --> METRIC1
    S3 --> METRIC2
    S5 --> METRIC3
    S4 --> PROACT_TUNE

    METRIC1 --> PROMPT_TUNE
    METRIC2 --> RAG_UPDATE
    METRIC3 --> PROMPT_TUNE

    S3 --> RAG_UPDATE
    RAG_UPDATE --> SLIDE_UPDATE

    RAG_UPDATE & PROMPT_TUNE & PROACT_TUNE & SLIDE_UPDATE --> FLYWHEEL
    FLYWHEEL --> INTERACT

    classDef positive fill:#d4edda,stroke:#28a745,color:#155724
    classDef negative fill:#f8d7da,stroke:#dc3545,color:#721c24
    classDef metric fill:#e2e3e5,stroke:#6c757d,color:#383d41
    classDef improve fill:#cce5ff,stroke:#004085,color:#004085
    classDef flywheel fill:#e8d5f5,stroke:#6f42c1,color:#3d0066

    class S1,S5 positive
    class S2,S3,S4 negative
    class METRIC1,METRIC2,METRIC3 metric
    class RAG_UPDATE,PROMPT_TUNE,PROACT_TUNE,SLIDE_UPDATE improve
    class FLYWHEEL flywheel
```

---

## Tóm tắt các paths

| Sơ đồ | Happy | Low-confidence | Failure | Correction |
|-------|-------|----------------|---------|------------|
| F1 — Giải thích | AI trả lời đúng + nguồn → Đã hiểu | Trả lời + banner vàng cảnh báo | Không tìm thấy trong RAG → từ chối | Sinh viên báo sai → correction log |
| F2 — Gợi ý chủ động | Sinh viên chấp nhận chip → F1 | Không đủ context → không gợi ý | Gợi ý sai khái niệm → dismiss | Dismiss → giảm probability proactive |
| F3 — Follow-up | Multi-turn rõ ràng, đào sâu | ≥3 lượt cùng khái niệm → escalate sang video | AI mất context, lạc đề | Reset hội thoại, hỏi lại rõ hơn |
