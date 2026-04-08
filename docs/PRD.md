
# 📄 PRD – AI Adaptive Learning Platform (MVP)

## 1. 🎯 Product Overview

**Product Name (working):** AI Adaptive Tutor

**Vision:**
Xây dựng nền tảng học tập cá nhân hoá, giúp mỗi học sinh học đúng thứ họ cần, đúng thời điểm.

**Goal của MVP:**
Validate rằng:

* Người học **có nhu cầu được cá nhân hoá**
* AI có thể **đề xuất nội dung + quiz phù hợp**
* User **cảm thấy tiến bộ rõ ràng**

---

## 2. 🚨 Problem Statement

Hiện tại, học sinh gặp các vấn đề:

* Không biết mình yếu ở đâu
* Nội dung học không phù hợp với level
* Không có feedback tức thì khi làm bài
* Không có người hướng dẫn 24/7

👉 Hệ quả:

* Học lan man
* Mất động lực
* Không tối ưu thời gian học

---

## 3. 👤 Target Users

### Primary User

* Học sinh (cấp 2 – đại học)
* Tự học (không có gia sư thường xuyên)

### User Traits

* Học online / YouTube / tài liệu rời rạc
* Không có lộ trình rõ ràng
* Muốn cải thiện nhanh (thi cử, kỹ năng)

---

## 4. 💡 Value Proposition

> “Học đúng thứ bạn yếu, với lộ trình riêng cho bạn – có AI hướng dẫn 24/7”

---

## 5. 🧩 Core Use Cases (MVP chỉ tập trung 2 cái)

### Use Case 1: Diagnostic + Adaptive Path

* User làm quiz ban đầu
* Hệ thống xác định:

  * Level
  * Điểm yếu
* Đề xuất lộ trình học cá nhân hoá

---

### Use Case 2: Learn + Instant Feedback

* User học theo nội dung được đề xuất
* Làm quiz tương ứng
* Nhận:

  * Feedback ngay lập tức
  * Giải thích
  * Gợi ý học tiếp

---

## 6. 🔄 UX Flow (MVP)

### Flow 1: Onboarding + Assessment

1. Vào app
2. Chọn môn học
3. Làm bài test nhanh (5–10 câu)
4. Xem:

   * Level
   * Điểm yếu
5. Nhận lộ trình học

---

### Flow 2: Learning Loop (Core loop 🔥)

1. Chọn bài học được đề xuất
2. Học nội dung (text / AI explain)
3. Làm quiz
4. Nhận feedback ngay:

   * Đúng / sai
   * Giải thích
5. Update:

   * Skill level
   * Next recommendation

👉 Loop này là “trái tim” của sản phẩm

---

## 7. 🧱 Feature Scope (MVP)

### ✅ Must-have

#### 1. Diagnostic Quiz

* Bộ câu hỏi phân loại level
* Mapping câu hỏi → skill

#### 2. User Skill Profile

* Lưu:

  * Level theo skill
  * Điểm yếu

#### 3. Adaptive Recommendation Engine (basic rule-based)

* Input:

  * Kết quả quiz
* Output:

  * Next lesson
  * Next quiz

#### 4. Learning Content (basic)

* Text / AI-generated explanation

#### 5. Quiz Engine

* Multiple choice
* Chấm điểm ngay

#### 6. Instant Feedback

* Giải thích câu trả lời
* Highlight sai đúng

---

### ❌ Not in MVP (rất quan trọng)

* Social / leaderboard
* Gamification phức tạp
* Video content xịn
* ML model phức tạp (chỉ cần rule-based)
* Chat AI full tutor (chỉ cần explain)

---

## 8. 🏗️ Architecture (MVP – tối giản nhưng đúng hướng)

### High-level Architecture

```
Frontend (Angular)
    ↓
Backend API (FastAPI)
    ↓
Services:
    - Quiz Engine
    - Recommendation Engine (rule-based)
    - AI Explanation Service
    ↓
Database (PostgreSQL / MongoDB)
```

---

### 🧩 Components

#### 1. Frontend (Angular)

* Quiz UI
* Learning screen
* Progress screen

---

#### 2. Backend (FastAPI)

Core APIs:

* `/diagnostic`
* `/submit-quiz`
* `/get-recommendation`
* `/get-explanation`

---

#### 3. Recommendation Engine (MVP logic)

Rule-based đơn giản:

* Nếu sai nhiều skill A → học lại A
* Nếu đúng > threshold → lên level

👉 Sau này mới upgrade → ML

---

#### 4. AI Service

* Generate explanation:

  * Tại sao sai
  * Cách làm đúng

---

#### 5. Database Schema (simple)

**User**

* id
* current_level

**Skill**

* id
* name

**UserSkill**

* user_id
* skill_id
* score

**Question**

* id
* skill_id
* difficulty

**Attempt**

* user_id
* question_id
* correct

---

## 9. 📊 Success Metrics (MVP validation)

### Activation

* % user hoàn thành diagnostic

### Engagement

* Số vòng learning loop / user

### Retention

* User quay lại sau 1–3 ngày

### Learning signal (proxy)

* Accuracy tăng theo thời gian

---

## 10. 🚀 MVP Scope Summary

👉 MVP này chỉ cần chứng minh 1 điều:

> “Adaptive learning + feedback tức thì → giúp user học hiệu quả hơn”

---
