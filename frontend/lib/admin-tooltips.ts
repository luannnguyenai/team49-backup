import type { KpiTooltip } from "@/components/admin/KpiCard";

export const overviewTooltips = {
  totalUsers: {
    summary: "Tổng số người dùng đã được tạo trong hệ thống.",
    detail: "Đếm từ bảng users. Đây là chỉ số cộng dồn, không phản ánh mức độ active hiện tại.",
  },
  dau: {
    summary: "Số người dùng hoạt động trong 24 giờ gần nhất.",
    detail: "Ước tính từ sessions theo user distinct trong 24 giờ. Hữu ích để theo dõi usage ngắn hạn.",
  },
  mau: {
    summary: "Số người dùng hoạt động trong 30 ngày gần nhất.",
    detail: "Ước tính từ sessions theo user distinct trong 30 ngày. Dùng để nhìn mức độ giữ chân tổng quát.",
  },
  signups7d: {
    summary: "Số người dùng đăng ký mới trong 7 ngày gần nhất.",
    detail: "Đếm từ users.created_at. Dùng để theo dõi tăng trưởng đầu vào.",
  },
  activeNow: {
    summary: "Số người dùng được xem là đang hoạt động lúc này.",
    detail: "Ước tính từ session gần đây hoặc session chưa đóng trong khoảng ngắn. Đây là tín hiệu near-real-time, không phải số tuyệt đối chính xác.",
  },
  llmCalls24h: {
    summary: "Tổng số lượt gọi LLM trong 24 giờ gần nhất.",
    detail: "Đếm từ dữ liệu lịch sử hỏi đáp. Dùng để theo dõi tải AI và mức sử dụng tutor.",
  },
  modelCurrent: {
    summary: "Model mặc định backend đang cấu hình để phục vụ request.",
    detail: "Lấy từ config runtime. Đây là thông tin cấu hình, không phải metric hiệu năng.",
  },
  errorRate: {
    summary: "Tỷ lệ request backend bị lỗi phía server.",
    detail: "Tính từ HTTP 5xx trên tổng request trong 5 phút gần nhất từ Prometheus. Nếu tăng liên tục thì cần kiểm tra backend hoặc upstream.",
  },
} satisfies Record<string, KpiTooltip>;

export const llmTooltips = {
  callsWindow: {
    summary: "Tổng số lượt gọi LLM trong cửa sổ thời gian đang xem.",
    detail: "Hiện đang tổng hợp theo 24 giờ từ qa_history.jsonl. Dùng để theo dõi lưu lượng tutor AI.",
  },
  errorsWindow: {
    summary: "Số lượt gọi LLM bị đánh dấu lỗi trong cửa sổ thời gian.",
    detail: "Đọc từ log qa_history.jsonl. Nếu tăng, cần đối chiếu với latency, provider status và log chi tiết.",
  },
  firstStatusP95: {
    summary: "95% request nhận được tín hiệu trạng thái đầu tiên nhanh hơn mốc này.",
    detail: "Tính từ Prometheus theo bucket 1 giờ. Đây là tín hiệu đầu tiên của stream bắt đầu phản hồi.",
  },
  firstStatusP50: {
    summary: "Một nửa request nhận được tín hiệu trạng thái đầu tiên nhanh hơn mốc này.",
    detail: "Giúp nhìn độ trễ điển hình thay vì chỉ nhìn tail latency.",
  },
  firstAnswerP95: {
    summary: "95% request nhận được phần nội dung trả lời đầu tiên nhanh hơn mốc này.",
    detail: "Đây gần với TTFT trong streaming tutor. Nếu tăng cao, trải nghiệm người dùng sẽ thấy chậm rõ rệt.",
  },
  firstAnswerP50: {
    summary: "Một nửa request nhận được phần nội dung trả lời đầu tiên nhanh hơn mốc này.",
    detail: "Phản ánh tốc độ phản hồi điển hình của tutor trong điều kiện bình thường.",
  },
  positiveRatings: {
    summary: "Số lượt phản hồi tích cực từ người dùng.",
    detail: "Đếm từ qa_history.rating = 1 trong 14 ngày gần nhất. Dùng để theo dõi chất lượng cảm nhận.",
  },
  negativeRatings: {
    summary: "Số lượt phản hồi tiêu cực từ người dùng.",
    detail: "Đếm từ qa_history.rating = -1 trong 14 ngày gần nhất. Nên đọc cùng recent negative feedback để hiểu nguyên nhân.",
  },
  positiveRatio: {
    summary: "Tỷ lệ phản hồi tích cực trên tổng phản hồi đã được chấm.",
    detail: "Tính từ positive trên total rated trong 14 ngày. Hữu ích hơn khi xem cùng sample size.",
  },
  unrated24h: {
    summary: "Số lượt trả lời chưa được người dùng đánh giá trong 24 giờ gần nhất.",
    detail: "Dùng để biết bao nhiêu interaction chưa có feedback, không đồng nghĩa với tốt hay xấu.",
  },
} satisfies Record<string, KpiTooltip>;

export const trafficTooltips = {
  rps1m: {
    summary: "Số request backend trung bình mỗi giây trong 1 phút gần nhất.",
    detail: "Lấy từ Prometheus rate. Dùng để theo dõi tải hệ thống theo thời gian thực.",
  },
  p50Latency: {
    summary: "Một nửa request hoàn thành nhanh hơn mốc này.",
    detail: "Phản ánh độ trễ điển hình của API từ Prometheus trong cửa sổ 5 phút.",
  },
  p95Latency: {
    summary: "95% request hoàn thành nhanh hơn mốc này.",
    detail: "Dùng để theo dõi tail latency. Nếu tăng, một nhóm người dùng sẽ cảm thấy hệ thống chậm rõ rệt.",
  },
  p99Latency: {
    summary: "99% request hoàn thành nhanh hơn mốc này.",
    detail: "Nhạy với outlier và spike. Hữu ích để phát hiện sự cố ngắt quãng.",
  },
  rate4xx: {
    summary: "Tỷ lệ request bị từ chối hoặc sai từ phía client.",
    detail: "Tính từ HTTP 4xx trên tổng request trong 5 phút. Tăng cao có thể do auth, route sai hoặc misuse từ frontend.",
  },
  rate5xx: {
    summary: "Tỷ lệ request lỗi phía server.",
    detail: "Tính từ HTTP 5xx trên tổng request trong 5 phút. Đây là chỉ báo chính cho backend instability.",
  },
} satisfies Record<string, KpiTooltip>;

export const systemTooltips = {
  cpuUsage: {
    summary: "Mức sử dụng CPU hiện tại của máy hoặc runtime backend.",
    detail: "Lấy từ psutil. Dùng để phát hiện tải xử lý tăng cao hoặc saturation.",
  },
  ramUsage: {
    summary: "Tỷ lệ bộ nhớ đang được sử dụng.",
    detail: "Lấy từ psutil. Nếu tăng liên tục có thể là dấu hiệu memory pressure hoặc leak.",
  },
  diskUsage: {
    summary: "Tỷ lệ dung lượng đĩa đang dùng.",
    detail: "Lấy từ psutil. Quan trọng với môi trường local hoặc container nếu log hoặc data tăng nhanh.",
  },
  dbConnections: {
    summary: "Số kết nối hiện có tới PostgreSQL.",
    detail: "Đọc từ pg_stat_activity. Nếu tăng bất thường có thể liên quan connection leak hoặc tải cao.",
  },
  redisHitRate: {
    summary: "Tỷ lệ cache hit của Redis trên tổng hit và miss.",
    detail: "Lấy từ Redis INFO stats. Cao hơn thường tốt hơn, nhưng cần đọc cùng loại workload.",
  },
  serviceUptime: {
    summary: "Thời gian backend process hiện tại đã chạy liên tục.",
    detail: "Tính từ lúc app boot. Nếu thường xuyên reset về thấp, có thể app đang restart.",
  },
} satisfies Record<string, KpiTooltip>;
