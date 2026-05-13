# AWS Cost Analysis for ECS Deployment

## 1. Executive Summary

Tài liệu này phân tích chi phí triển khai AWS cho dự án dựa trên cấu hình hiện có trong `deploy-ecs/`:

- `Region`: `ap-southeast-1` (Singapore)
- `Compute`: `2` dịch vụ `ECS Fargate` luôn bật
  - `a20-backend`: `1 vCPU / 2 GB`
  - `a20-frontend`: `0.5 vCPU / 1 GB`
- `Ingress`: `1` public `Application Load Balancer`
- `Network egress`: `1` `NAT Gateway`
- `Database`: `RDS PostgreSQL db.t4g.micro`, `20 GB gp3`
- `Cache`: `ElastiCache Redis cache.t4g.micro`
- `Assets`: `S3 + CloudFront`
- `Secrets`: `Secrets Manager`
- `Logs`: `CloudWatch Logs`

Kết luận ngắn gọn cho stakeholders:

- Chi phí nền tối thiểu để giữ môi trường production chạy liên tục hiện vào khoảng **$168/tháng**.
- Khi có traffic thật, chi phí sẽ tăng chủ yếu theo `CloudFront bandwidth`, `CloudWatch log ingestion`, `NAT data processing`, và `ALB LCU`.
- Với cấu hình hiện tại, mức ngân sách thực tế nên chuẩn bị là:
  - **Low usage**: khoảng **$178/tháng**
  - **Expected usage**: khoảng **$225/tháng**
  - **High usage**: khoảng **$359/tháng**

Các con số trên là mô hình baseline để present và ra quyết định ngân sách, không phải invoice forecast tuyệt đối. Mục tiêu là chỉ ra cost drivers chính và ngưỡng tăng chi phí khi scale.

## 2. Current AWS Footprint

Phân tích này bám đúng thiết kế trong repo:

- `deploy-ecs/terraform/live/prod/main.tf`
- `deploy-ecs/terraform/live/prod/terraform.tfvars.example`
- `deploy-ecs/terraform/modules/database/main.tf`
- `deploy-ecs/terraform/modules/cache/main.tf`
- `deploy-ecs/terraform/modules/network/main.tf`
- `deploy-ecs/terraform/modules/alb/main.tf`
- `deploy-ecs/terraform/modules/assets/main.tf`
- `deploy-ecs/terraform/modules/observability/main.tf`

Những điểm ảnh hưởng trực tiếp đến cost:

- `ECS Cluster` không có phí control plane riêng, nhưng `Fargate` tính phí theo `vCPU-hour` và `GB-hour`.
- `NAT Gateway` đang bật mặc định để task trong private subnets kéo image từ `ECR`, đọc `Secrets Manager`, ghi `CloudWatch Logs`, và gọi external providers.
- `CloudFront` đang cấu hình `PriceClass_100`, nghĩa là ưu tiên edge ở `US + Europe` để giảm cost, không phải cấu hình tối ưu latency cho người dùng Đông Nam Á.
- `RDS` đang là `Single-AZ`, chưa phải cấu hình HA đầy đủ kiểu production enterprise.
- `Observability stack` là tùy chọn, chưa bật mặc định; nếu bật sẽ tăng baseline rõ rệt.

## 3. Monthly Fixed Baseline

Đây là phần chi phí gần như phải trả ngay cả khi traffic còn thấp.

Assumption tính tháng:

- `730` giờ / tháng
- `2` secrets hoạt động tối thiểu:
  - `backend_secret_arn`
  - `RDS managed master secret`
- Chưa tính custom domain, Route 53 hosted zone, và observability stack tùy chọn vào baseline cốt lõi

| Thành phần | Cấu hình hiện tại | Rate | Ước tính / tháng |
|---|---|---:|---:|
| ECS Fargate backend | `1 vCPU + 2 GB`, always on | `$0.05056/vCPU-hr` + `$0.00553/GB-hr` | **$44.98** |
| ECS Fargate frontend | `0.5 vCPU + 1 GB`, always on | cùng rate | **$22.49** |
| ALB fixed hourly | `1` ALB | `$0.0252/hr` | **$18.40** |
| NAT Gateway fixed hourly | `1` NAT Gateway | `$0.059/hr` | **$43.07** |
| RDS PostgreSQL compute | `db.t4g.micro` | `$0.025/hr` | **$18.25** |
| RDS storage | `20 GB gp3` | `$0.138/GB-mo` | **$2.76** |
| ElastiCache Redis | `cache.t4g.micro` | `$0.024/hr` | **$17.52** |
| Secrets Manager | `2` secrets | `$0.40/secret-mo` | **$0.80** |
| **Total fixed baseline** |  |  | **$168.27 / tháng** |

Stakeholder takeaway:

- Dù traffic còn nhỏ, nền hạ tầng production theo kiến trúc hiện tại đã ở vùng **~$170/tháng**.
- Hai cost cố định đáng chú ý nhất là:
  - `Fargate app runtime`: khoảng **$67.47/tháng**
  - `NAT Gateway`: khoảng **$43.07/tháng**

## 4. Variable Cost Model

Đây là các biến phí tăng theo usage thật.

### 4.1 CloudFront

CloudFront không có phí cố định đáng kể, nhưng là cost driver lớn nhất khi dự án bắt đầu phục vụ video/assets thực tế.

Rate tham chiếu quan trọng:

- `Asia Pacific` data transfer out: **$0.120/GB**
- `US/Europe` data transfer out: **$0.085/GB**
- `Asia Pacific` HTTPS GET/HEAD requests: **$0.012 / 10,000 requests**

Ý nghĩa với dự án:

- Vì kiến trúc đã tách video/assets ra `CloudFront -> Browser`, chi phí băng thông user-facing chủ yếu sẽ dồn vào `CloudFront`, không phải backend ECS.
- Đây là hướng đúng về kỹ thuật vì tránh đẩy video qua FastAPI, nhưng ngân sách bandwidth phải được theo dõi riêng.
- `PriceClass_100` giúp hạ cost CDN, nhưng đánh đổi latency cho người dùng châu Á. Nếu tệp người dùng chính là Việt Nam/SEA, về sau có thể phải cân nhắc giữa `chi phí` và `trải nghiệm`.

### 4.2 NAT Gateway data processing

Ngoài phí fixed theo giờ, NAT còn tính theo dữ liệu đi qua:

- `NAT data processing`: **$0.059/GB**

Các luồng gây phí NAT trong dự án này:

- Gọi `LLM providers`
- Gọi email provider
- Pull image / push logs / secrets access trong runtime
- Outbound API traffic nói chung từ backend và frontend tasks

Lưu ý:

- Rate `$0.059/GB` là phí xử lý qua NAT.
- Chi phí `Data Transfer Out to Internet` tiêu chuẩn của AWS có thể còn phát sinh thêm trong một số luồng, nhưng thường không phải cost driver chính ở giai đoạn đầu nếu payload API nhỏ hơn nhiều so với video delivery qua CloudFront.

### 4.3 ALB LCUs

ALB ngoài phí fixed còn có phí theo năng lực sử dụng:

- `ALB LCU`: **$0.008/LCU-hour**

Biến phí này tăng theo:

- số kết nối mới
- số kết nối đồng thời
- số bytes xử lý
- số rule evaluations

Với traffic thấp, khoản này thường nhỏ. Khi API/chat traffic tăng đáng kể, ALB LCU sẽ bắt đầu nhìn thấy rõ trên bill.

### 4.4 S3

Rate chính:

- `S3 Standard storage`: **$0.025/GB-month**
- `PUT/COPY/POST/LIST`: **$0.005/1,000 requests**
- `GET and other requests`: **$0.004/10,000 requests**

Ý nghĩa với dự án:

- `S3 storage` thường không phải cost driver số một ở giai đoạn đầu.
- Khi số lượng video và course assets tăng nhanh, S3 vẫn tăng đều theo dung lượng lưu trữ.
- Nếu pipeline upload lại assets nhiều lần hoặc versioning phình ra, S3 cost có thể tăng âm thầm.

### 4.5 CloudWatch Logs

Rate chính:

- `Log ingestion`: **$0.70/GB**
- `Log storage`: **$0.03/GB-month**

Ý nghĩa với dự án:

- Với ứng dụng AI/chat, log dễ phình do request traces, prompt debugging, retries, agent telemetry.
- Trong repo hiện log retention đang đặt `7 ngày`, đây là quyết định tốt để giữ chi phí thấp hơn.
- Nếu bật nhiều debug logs trong production, `CloudWatch ingestion` có thể trở thành cost driver lớn hơn mong đợi.

### 4.6 ECR

Rate chính:

- `ECR image storage`: **$0.10/GB-month**

Ý nghĩa với dự án:

- Khoản này thường nhỏ hơn bandwidth và compute.
- Nếu giữ nhiều image tags, multi-stage images lớn, hoặc không cleanup lifecycle policy đều đặn thì ECR cost sẽ tăng dần.

## 5. Scenario Modeling for Stakeholders

Ba kịch bản dưới đây dùng để nói chuyện với stakeholders về mức ngân sách theo tăng trưởng usage.

### 5.1 Low usage

Assumption:

- `50 GB` CloudFront egress / tháng
- `500,000` CloudFront HTTPS requests / tháng
- `10 GB` data qua NAT / tháng
- `2 GB` log ingestion / tháng
- `0.5 GB` log storage trung bình / tháng
- `10 GB` S3 storage
- `50,000` S3 GET requests
- `5,000` S3 PUT/LIST requests
- `5 GB` ECR storage
- `50 LCU-hours` ALB usage / tháng

Ước tính:

- Fixed baseline: **$168.27**
- Variable usage: **$9.80**
- **Tổng: $178.07 / tháng**

### 5.2 Expected usage

Assumption:

- `300 GB` CloudFront egress / tháng
- `5,000,000` CloudFront HTTPS requests / tháng
- `50 GB` data qua NAT / tháng
- `10 GB` log ingestion / tháng
- `2.5 GB` log storage trung bình / tháng
- `50 GB` S3 storage
- `1,000,000` S3 GET requests
- `50,000` S3 PUT/LIST requests
- `10 GB` ECR storage
- `200 LCU-hours` ALB usage / tháng

Ước tính:

- Fixed baseline: **$168.27**
- Variable usage: **$56.53**
- **Tổng: $224.79 / tháng**

### 5.3 High usage

Assumption:

- `1 TB` CloudFront egress / tháng
- `20,000,000` CloudFront HTTPS requests / tháng
- `200 GB` data qua NAT / tháng
- `30 GB` log ingestion / tháng
- `7.5 GB` log storage trung bình / tháng
- `200 GB` S3 storage
- `5,000,000` S3 GET requests
- `200,000` S3 PUT/LIST requests
- `20 GB` ECR storage
- `500 LCU-hours` ALB usage / tháng

Ước tính:

- Fixed baseline: **$168.27**
- Variable usage: **$191.03**
- **Tổng: $359.29 / tháng**

## 6. Biggest Cost Drivers

Theo kiến trúc hiện tại, cost drivers nên được theo dõi theo thứ tự:

1. `CloudFront data transfer out`
2. `Fargate always-on compute`
3. `NAT Gateway`
4. `CloudWatch log ingestion`
5. `RDS + Redis`

Diễn giải thực tế:

- Khi sản phẩm còn ít traffic, `compute + NAT` là phần “đốt tiền nền”.
- Khi sản phẩm bắt đầu có người dùng thật, `CloudFront bandwidth` sẽ vượt lên nhanh nhất.
- Khi team bật nhiều observability/debugging cho AI flows, `CloudWatch` có thể tăng bất ngờ.

## 7. Sensitivity Analysis

Một số “đòn bẩy” giúp stakeholders hiểu mỗi quyết định scale sẽ thêm bao nhiêu tiền:

- Thêm `1` backend replica luôn bật cùng cấu hình hiện tại:
  - khoảng **+$44.98/tháng**
- Thêm `1` frontend replica luôn bật:
  - khoảng **+$22.49/tháng**
- Thêm `1` NAT Gateway để tăng HA đa AZ:
  - khoảng **+$43.07/tháng** fixed, chưa tính data processing
- Tăng thêm `100 GB` CloudFront egress tại `Asia Pacific`:
  - khoảng **+$12/tháng**
- Tăng thêm `10 GB` CloudWatch log ingestion:
  - khoảng **+$7/tháng**
- Tăng thêm `100 GB` data qua NAT:
  - khoảng **+$5.90/tháng**

## 8. Optional Cost: Observability Stack

Repo có sẵn stage observability riêng với:

- `Prometheus`
- `Loki`
- `Grafana`
- `postgres-exporter`
- `redis-exporter`
- `EFS`

Nếu bật stack này theo cấu hình mặc định hiện tại:

- `5` Fargate tasks cỡ `0.25 vCPU / 0.5 GB`
- Chi phí compute tăng khoảng **+$56.23/tháng**
- Nếu dùng khoảng `20 GB` `EFS Standard`, thêm khoảng **+$7.20/tháng**
- Chưa tính log ingestion phát sinh thêm

Nói cách khác:

- Bật observability stack đầy đủ có thể đẩy baseline từ **~$168** lên vùng **~$230+ / tháng** ngay cả trước khi traffic tăng đáng kể.

## 9. Recommendations

Đề xuất dùng trong buổi present:

- Ngắn hạn, nên communicate ngân sách production nền là **$170-$225/tháng** cho giai đoạn early rollout.
- Nên reserve vùng **$225-$360/tháng** khi đã có traffic thật, assets/video bắt đầu được truy cập thường xuyên, và log production tăng.
- Nếu stakeholder muốn “production-like” nhưng tiết kiệm hơn, chi phí nên tối ưu theo thứ tự:
  - giảm `NAT Gateway` dependency bằng `VPC endpoints` cho `ECR`, `CloudWatch Logs`, `Secrets Manager`, `S3`
  - giữ `CloudWatch` retention ngắn và tránh bật debug logs kéo dài
  - bật `ECR lifecycle policy` chặt hơn
  - chỉ bật full observability stack khi cần monitoring chủ động

## 10. Decision Framing for Stakeholders

Kiến trúc hiện tại là một baseline hợp lý nếu mục tiêu là:

- học và vận hành `AWS managed stack` bài bản
- có đường lên production thực tế
- tách `video delivery` khỏi backend để scale đúng

Nhưng stakeholders cần hiểu rõ:

- Đây không phải cấu hình “rẻ nhất có thể”
- Đây là cấu hình “production-structured, still moderate-cost”
- Chi phí sẽ tăng chủ yếu theo `bandwidth`, không phải chỉ theo số EC2-like instances

Nếu cần một câu chốt để present:

> Với kiến trúc ECS hiện tại, dự án cần khoảng **$170/tháng** để giữ production luôn sẵn sàng, và nên dự trù thực tế **$225-$360/tháng** khi bắt đầu có usage thật và phân phối assets/video qua CloudFront.

## 11. Assumptions and Exclusions

Những gì chưa đưa sâu vào mô hình này:

- `Route 53` query charges
- `Internet Data Transfer Out` tiêu chuẩn ngoài phần NAT processing
- phần backup vượt free allowance của `RDS`
- `ACM` custom certificate scenarios khác
- `AWS Budgets` và email alert charges
- chi tiết cost theo `LLM provider` vì đó là vendor cost ngoài AWS

Nếu cần forecast sát hơn trước khi go-live, bước tiếp theo nên là:

- chốt traffic assumptions theo số MAU/DAU
- chốt dung lượng video/assets thật
- chốt tỷ lệ người dùng theo địa lý
- chạy lại mô hình bằng `AWS Pricing Calculator`

## 12. Pricing Sources

Nguồn rate chính thức đã dùng:

- AWS public price list:
  - `AmazonECS`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-southeast-1/index.json`
  - `AWSELB`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/ap-southeast-1/index.json`
  - `AmazonEC2` for NAT Gateway: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-southeast-1/index.json`
  - `AmazonRDS`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/ap-southeast-1/index.json`
  - `AmazonElastiCache`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonElastiCache/current/ap-southeast-1/index.json`
  - `AmazonS3`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/ap-southeast-1/index.json`
  - `AmazonCloudWatch`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/ap-southeast-1/index.json`
  - `AmazonECR`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECR/current/ap-southeast-1/index.json`
  - `AWSSecretsManager`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSSecretsManager/current/ap-southeast-1/index.json`
  - `AmazonRoute53`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRoute53/current/index.json`
  - `AmazonCloudFront`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudFront/current/index.json`
  - `AmazonEFS`: `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEFS/current/ap-southeast-1/index.json`
