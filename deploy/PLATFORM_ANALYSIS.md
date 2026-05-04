# Platform Analysis — Render vs Railway vs AWS

**Date:** 2026-05-03
**Stack:** FastAPI + Postgres (pgvector) + Redis + Next.js
**Data:** ~15GB MP4 video files (self-hosted)
**Constraint:** AWS credits available

---

## TL;DR

> **Deploy lên AWS** (App Runner + RDS + S3 + CloudFront).
> Lý do: video MP4 streaming khiến egress là cost driver chính. App phải cùng region với S3 để egress S3→app = **free**. Railway/Render khiến mỗi GB phải trả egress 2 lần.

---

## 1. So sánh ban đầu — Render vs Railway

| Tiêu chí | **Railway** | **Render** |
|---|---|---|
| Multi-service từ docker-compose | Tốt — deploy từng service riêng, env share dễ | Phải tách thành Web/Worker service trong `render.yaml` |
| Postgres + **pgvector** | Có (Postgres 16, bật extension được) | Có (managed Postgres hỗ trợ pgvector) |
| Redis managed | Có (plugin native) | Có (Key Value service) |
| Free tier | $5 credit/tháng | Free web service **sleep sau 15 phút idle** (cold start ~30s) |
| Pricing thực tế | Pay-as-you-go theo RAM/CPU/giờ | Flat $7/service/tháng (Starter) |
| Build từ Dockerfile | Native, nhanh | Native, build chậm hơn |
| Private networking | Có (`.railway.internal`) | Có (internal hostname) |
| Region gần VN | US/EU/**SG** | Oregon/Frankfurt/**SG** |
| Logs/metrics UI | Gọn, realtime tốt | Đủ dùng, ít trực quan hơn |

**Verdict (không có data lớn):** Railway tốt hơn — pay-as-you-go rẻ hơn cho stack 4 services, không cold-start, có Singapore region.

---

## 2. Vấn đề Egress với 15GB Video MP4

Video streaming = bandwidth-heavy. Nếu app ở Railway/Render còn data ở AWS S3:

```
S3 (AWS)  →  Railway/Render (cloud khác)  →  User
        $0.09/GB egress              $0.09/GB egress
```

**Mỗi GB user xem = trả egress 2 lần.**

### Estimate:

| Traffic | Egress S3→App | Egress App→User | **Total/tháng** |
|---|---|---|---|
| 100 user/ngày × 500MB | $135 | $135 | **$270** |
| 50 user/ngày × 200MB | $27 | $27 | **$54** |
| 1000 user/ngày × 1GB | $2,700 | $2,700 | **$5,400** |

→ Egress **giết chết kinh tế** nếu app không cùng cloud với S3.

**Kết luận:** Khi data lớn + bandwidth-heavy → app phải cùng region/cloud với storage.

---

## 3. Storage Options Comparison (15GB)

| Provider | Storage 15GB/tháng | Egress | Phù hợp |
|---|---|---|---|
| **AWS S3 Standard** | $0.345 | $0.09/GB | ⭐ Có credit AWS |
| **Cloudflare R2** | $0.225 | **Free** | Nếu app KHÔNG ở AWS |
| **Backblaze B2** | $0.09 | $0.01/GB | Storage rẻ, ít traffic |
| **AWS S3 + CloudFront** | $0.345 + $0.085/GB cached | **Free S3→CF** | ⭐⭐ Best cho video MP4 |

**Cho user case này: AWS S3 + CloudFront** (tận dụng credit + cache rate cao cho video).

---

## 4. AWS Deployment Options

### Option A — **App Runner** ⭐ Recommended

Đơn giản nhất, gần Railway nhất.

| Component | Service | Spec | ~Cost/month |
|---|---|---|---|
| FastAPI backend | **App Runner** (Dockerfile) | 1 vCPU / 2GB | ~$25 |
| Next.js frontend | **App Runner** hoặc **Amplify Hosting** | 0.5 vCPU / 1GB | ~$10–15 |
| Postgres + pgvector | **RDS Postgres** db.t4g.micro | 1 vCPU / 1GB | ~$15 |
| Redis | **ElastiCache** cache.t4g.micro | OR self-hosted Redis trong App Runner | ~$12 (or $0) |
| Video 15GB | **S3 Standard** | 15GB | ~$0.35 |
| CDN | **CloudFront** | Cache + signed URLs | ~$5–20 (depends traffic) |

**Tổng ước tính:** $65–90/tháng (credit cover được nhiều tháng).

**Ưu điểm:**
- App ↔ S3 same-region: **egress S3 → App Runner = FREE**.
- Auto-scale, HTTPS sẵn, deploy từ Dockerfile.
- Native VPC integration với RDS.

**Nhược điểm:**
- Ít flexible hơn ECS Fargate.
- Cold-start nhỏ khi scale-to-zero (nếu enable).

### Option B — **ECS Fargate + ALB**

Full control, multi-container 1-1 với `docker-compose.yml`.

- Task definition cho mỗi service (backend, frontend).
- ALB route traffic.
- Setup phức tạp ~2× App Runner.
- **Tổng:** ~$80–120/tháng.

**Khi chọn:** Cần fine-grained control, planning scale lớn.

### Option C — **Lightsail Containers**

Rẻ nhất, predictable cost, **bundled egress**.

- $7–40/tháng flat fee tùy plan.
- **TB egress free** mỗi tháng theo plan.
- Bundled DB option (Lightsail Database).
- **Tổng:** ~$30–60/tháng.

**Khi chọn:** Muốn cost predictable, không sợ bill bất ngờ, ít DevOps.

---

## 5. Architecture đề xuất (Option A)

```
                          ┌──────────────────┐
                          │   CloudFront     │ ← signed URLs, edge cache
                          │   (CDN)          │
                          └────────┬─────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
        ┌─────────▼──────────┐           ┌──────────▼─────────┐
        │  S3 (videos 15GB)  │           │   User Browser     │
        └────────────────────┘           └──────────┬─────────┘
                  ▲                                 │
                  │ free egress (same region)       │ HTTPS
                  │                                 │
        ┌─────────┴──────────────────────────────────▼─────────┐
        │                  AWS Region (ap-southeast-1)         │
        │                                                      │
        │  ┌──────────────────┐      ┌──────────────────┐     │
        │  │ App Runner:      │      │ App Runner:      │     │
        │  │ Next.js frontend │─────▶│ FastAPI backend  │     │
        │  └──────────────────┘      └────────┬─────────┘     │
        │                                     │               │
        │                          ┌──────────┴──────────┐    │
        │                          │                     │    │
        │                  ┌───────▼────────┐  ┌─────────▼──┐ │
        │                  │ RDS Postgres   │  │ ElastiCache│ │
        │                  │ (pgvector)     │  │ Redis      │ │
        │                  └────────────────┘  └────────────┘ │
        └──────────────────────────────────────────────────────┘
```

**Region:** `ap-southeast-1` (Singapore) — gần VN nhất.

---

## 6. CloudFront cho Video MP4 — Bắt buộc

Không stream trực tiếp từ S3. CloudFront giảm egress 5–10×:

| Path | Cost/GB |
|---|---|
| S3 → User trực tiếp | $0.09/GB |
| S3 → CloudFront → User | $0.085/GB + **cache hit FREE** |

**Cache hit rate video thường 70–90%** → effective cost ~$0.01–0.03/GB.

### Implementation pattern:

```python
# src/services/video_service.py
from botocore.signers import CloudFrontSigner
from datetime import datetime, timedelta

def get_video_url(video_id: str, expires_in: int = 3600) -> str:
    """Trả signed CloudFront URL cho video."""
    signer = CloudFrontSigner(KEY_PAIR_ID, rsa_signer)
    url = f"https://{CLOUDFRONT_DOMAIN}/videos/{video_id}.mp4"
    return signer.generate_presigned_url(
        url,
        date_less_than=datetime.utcnow() + timedelta(seconds=expires_in),
    )
```

**Bonus features:** HTTPS, geo restriction, signed URLs chống hotlink, range requests cho seek video.

---

## 7. Decision Matrix

| Ưu tiên | Platform | Cost ước tính/tháng |
|---|---|---|
| **Đơn giản, có AWS credit** | ⭐ **AWS App Runner** | $65–90 |
| **Cost flat, predictable** | **AWS Lightsail Containers** | $30–60 |
| **Full control, scale lớn** | **AWS ECS Fargate** | $80–120 |
| Không có AWS credit, data nhỏ | Railway + R2 | $5–15 |
| Enterprise SLA, preview env | Render + R2 | $25+ |

---

## 8. Bước tiếp theo (recommended path)

1. **Setup AWS infra** (region `ap-southeast-1`):
   - Tạo S3 bucket cho videos.
   - Tạo CloudFront distribution với S3 origin + signed URL.
   - Tạo RDS Postgres (`db.t4g.micro`, enable `vector` extension).
   - Tạo ElastiCache Redis (hoặc self-host).
2. **Adapt code:**
   - Thêm `boto3` + S3 client trong `src/services/storage_service.py`.
   - Thêm CloudFront signed URL helper trong `src/services/video_service.py`.
   - Update env: `AWS_REGION`, `S3_BUCKET`, `CLOUDFRONT_DOMAIN`, `CLOUDFRONT_KEY_PAIR_ID`, `CLOUDFRONT_PRIVATE_KEY`.
3. **Deploy:**
   - Push images lên ECR.
   - Tạo App Runner service cho backend (point to ECR image, set env, connect VPC để reach RDS).
   - Tạo App Runner service cho frontend (hoặc Amplify Hosting).
4. **Migrate data:**
   - `pg_dump` từ local → upload S3 → restore vào RDS.
   - `aws s3 sync ./videos s3://bucket/videos/` (15GB ~30 phút).
5. **DNS + HTTPS:**
   - Route 53 hosted zone.
   - ACM cert cho domain.
   - Custom domain trỏ về App Runner.

---

## 9. Cost Monitoring

Bật **AWS Budget alerts** để theo dõi credit:
- Budget $10/tháng → alert.
- Budget 80% credit còn lại → alert.
- Cost Explorer review hàng tuần trong tháng đầu.

**Egress là rủi ro lớn nhất** — track CloudFront `BytesDownloaded` metric.

---

## Phụ lục — Tại sao KHÔNG chọn Railway/Render khi có data lớn

- **Railway/Render egress out:** $0.10/GB sau quota free.
- **Cross-cloud egress:** S3 (AWS) → Railway (GCP) tính cả 2 chiều.
- **Không có CDN tích hợp:** phải tự setup CloudFlare hoặc tương tự, thêm complexity.
- **Bandwidth không predictable:** 1 video viral có thể tốn $100+ trong 1 ngày.

→ Quy tắc: **storage và compute phải cùng cloud + cùng region** khi bandwidth-heavy.
