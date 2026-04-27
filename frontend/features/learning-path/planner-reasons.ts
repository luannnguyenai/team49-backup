export interface PlannerReasonDescription {
  label: string;
  details: string;
}

export function describePlannerReason(code: string): PlannerReasonDescription {
  switch (code) {
    case "critical_kp":
      return {
        label: "Critical KP",
        details: "Đơn vị này phủ knowledge point quan trọng cho path hiện tại.",
      };
    case "high_salience":
      return {
        label: "High salience",
        details: "Nội dung có độ liên quan cao với mục tiêu học.",
      };
    case "quiz_available":
      return {
        label: "Quiz available",
        details: "Có câu hỏi đánh giá phù hợp để xác thực mastery.",
      };
    case "required_prerequisite":
      return {
        label: "Prerequisite",
        details: "Đây là nền tảng cần có trước khi học phần sau.",
      };
    case "quick_review":
      return {
        label: "Quick review",
        details: "Mastery khá ổn, chỉ cần ôn nhanh.",
      };
    case "skip_by_mastery":
      return {
        label: "Skip by mastery",
        details: "Có evidence đủ mạnh để bỏ qua nội dung này.",
      };
    case "hidden_logistics":
      return {
        label: "Hidden logistics",
        details: "Bị loại khỏi path chính vì là logistics/admin, không phải learner skip.",
      };
    case "reference_only":
      return {
        label: "Reference",
        details: "Nội dung tham khảo, không ép học/quiz trong path chính.",
      };
    default:
      return {
        label: code,
        details: "Planner chưa có mô tả riêng cho reason code này.",
      };
  }
}
