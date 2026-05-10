# Platform Analysis — Why ECS Fargate

## Why not App Runner

App Runner triển khai nhanh hơn, nhưng giấu nhiều chi tiết vận hành. Nếu mục tiêu là vừa làm vừa học, nó không phơi bày đủ:

- task definition
- service rollout
- ALB health checks
- service autoscaling
- execution role vs task role
- network path giữa load balancer, task, DB, cache

## Why ECS Fargate

`ECS Fargate` giữ được phần học giá trị nhất của container production trên AWS, nhưng chưa bắt bạn quản lý EC2 nodes. Nó cân bằng tốt giữa:

- thực hành production concepts
- mức độ phức tạp chấp nhận được
- khả năng mở rộng sau này

## Why not ECS on EC2

ECS on EC2 thêm một lớp vận hành nữa:

- capacity planning
- AMI/patching
- instance lifecycle
- host security

Lớp này tốt để học sau, nhưng không cần cho production v1 của repo này.
