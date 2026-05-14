# GitHub Actions Runner Host

Các file trong thư mục này dựng một EC2 Ubuntu riêng cho self-hosted GitHub Actions runner của repo `A20-App-049`.

## Mục tiêu

- Tạo host runner riêng trong VPC production hiện có
- Đặt toàn bộ runtime dưới `/runner` để dễ theo dõi
- Cài sẵn các phụ thuộc cần cho workflow hiện tại:
  - Docker
  - Node.js 20
  - Python 3.12
  - Terraform
  - AWS CLI v2

## Khuyến nghị instance

- Mặc định: `c7i.xlarge`
- Fallback nếu AZ hiện tại không hỗ trợ: `m7i.xlarge`
- Fallback thấp hơn: `m6i.xlarge`

Lý do: workflow hiện tại cần Docker build, test backend với service containers, frontend type-check, và Terraform plan. `xlarge` 4 vCPU / 8 GiB là điểm cân bằng khá ổn để tránh nghẽn CPU khi build image.

## Các file

- `user-data.sh`: bootstrap máy Ubuntu khi EC2 vừa khởi tạo
- `launch-ec2-runner.ps1`: chạy từ máy local để tạo EC2 bằng AWS CLI
- `register-github-runner.sh`: chạy trên EC2 để đăng ký runner vào GitHub

## 1. Launch EC2

Ví dụ:

```powershell
pwsh -File .\runner\launch-ec2-runner.ps1 `
  -KeyName "<your-ec2-keypair-name>" `
  -InstanceProfileName "<optional-instance-profile-name>"
```

Script sẽ:

- đọc `deploy-ecs/terraform/live/prod/tf-outputs.json`
- lấy `vpc_id` và `public_subnet_ids[0]`
- resolve Ubuntu 24.04 AMI mới nhất từ SSM public parameter
- tạo security group `a20-gha-runner-sg` nếu chưa có
- mở SSH `22/tcp` cho IP public hiện tại của máy chạy script
- tạo EC2 với public IP và root volume `gp3 80 GiB`

## 2. SSH vào máy

```bash
ssh -i <your-key>.pem ubuntu@<public-ip>
```

Kiểm tra bootstrap:

```bash
cat /runner/bootstrap/versions.txt
docker --version
node --version
python3.12 --version
terraform version
aws --version
```

## 3. Register GitHub runner

```bash
chmod +x /path/to/repo/runner/register-github-runner.sh
sudo /path/to/repo/runner/register-github-runner.sh \
  https://github.com/a20-ai-thuc-chien/A20-App-049 \
  <registration-token> \
  a20-gha-runner-01 \
  self-hosted,linux,x64,aws,ec2
```

Nếu token cũ đã hết hạn, generate token mới tại:

- `Repo > Settings > Actions > Runners > New self-hosted runner`

## 4. Vị trí runner trên máy

- root: `/runner`
- app runner: `/runner/actions-runner`
- log/version bootstrap: `/runner/bootstrap`

## 5. Gợi ý tiếp theo

Sau khi runner online, hãy update workflow từ `[self-hosted]` sang label cụ thể hơn, ví dụ:

```yaml
runs-on: [self-hosted, linux, aws, ec2]
```
