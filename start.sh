#!/usr/bin/env bash
# =============================================================================
# start.sh — Khởi chạy toàn bộ AI Adaptive Learning Platform
# Chỉ cần chạy: bash start.sh
# =============================================================================
set -euo pipefail

# ── Màu sắc terminal ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BOLD}══════════════════════════════════════════${NC}"; echo -e "${BOLD}  $*${NC}"; echo -e "${BOLD}══════════════════════════════════════════${NC}"; }

# ── Thư mục gốc ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# BƯỚC 0 — Kiểm tra điều kiện tiên quyết
# =============================================================================
log_section "Bước 0 — Kiểm tra môi trường"

# Docker
if ! command -v docker &>/dev/null; then
  log_error "Docker chưa được cài đặt. Vui lòng cài Docker Desktop trước."
  exit 1
fi
if ! docker info &>/dev/null; then
  log_error "Docker daemon chưa chạy. Hãy khởi động Docker Desktop và thử lại."
  exit 1
fi
log_ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# Docker Compose
if ! docker compose version &>/dev/null; then
  log_error "Docker Compose v2 chưa được cài đặt."
  exit 1
fi
log_ok "$(docker compose version)"

# File .env
if [ ! -f ".env" ]; then
  log_warn "Chưa có file .env — đang copy từ .env.example..."
  cp .env.example .env
  log_warn "Vui lòng mở .env và điền GEMINI_API_KEY trước khi tiếp tục."
  exit 1
fi

# Kiểm tra GEMINI_API_KEY
GEMINI_KEY=$(grep -E '^GEMINI_API_KEY=' .env | cut -d= -f2 | tr -d '"' | tr -d "'")
if [ -z "$GEMINI_KEY" ] || [[ "$GEMINI_KEY" == AIza... ]] || [[ "$GEMINI_KEY" == sk-* ]]; then
  log_error "GEMINI_API_KEY chưa được cấu hình trong .env"
  log_error "Hãy điền giá trị thực: GEMINI_API_KEY=AIza..."
  exit 1
fi
log_ok "GEMINI_API_KEY đã cấu hình"

# Kiểm tra data
if [ -d "data/CS231n" ]; then
  VIDEO_COUNT=$(find data/CS231n/videos -name "*.mp4" 2>/dev/null | wc -l)
  TRANSCRIPT_COUNT=$(find data/CS231n/transcripts -name "*.txt" -o -name "*.json" 2>/dev/null | wc -l)
  log_ok "Data CS231n: ${VIDEO_COUNT} videos, ${TRANSCRIPT_COUNT} transcripts"
else
  log_warn "Không tìm thấy data/CS231n/ — AI Tutor sẽ không có bài giảng để truy vấn"
fi

# =============================================================================
# BƯỚC 1 — Khởi chạy services
# =============================================================================
log_section "Bước 1 — Build & Start Docker services"

log_info "Đang build và khởi chạy tất cả services (lần đầu ~3-5 phút)..."
# up --build tự recreate container nếu image thay đổi, giữ nguyên volumes (DB data).
# Dùng 'docker compose down' thủ công nếu muốn reset hoàn toàn (không xóa data).
# Dùng 'docker compose down -v' nếu muốn xóa cả data volumes.
docker compose up -d --build

# =============================================================================
# BƯỚC 2 — Chờ backend healthy
# =============================================================================
log_section "Bước 2 — Chờ services khởi động"

log_info "Chờ database (PostgreSQL) healthy..."
TIMEOUT=120
ELAPSED=0
until docker compose exec -T db pg_isready -U postgres -d ai_learning &>/dev/null; do
  if [ $ELAPSED -ge $TIMEOUT ]; then
    log_error "Database không healthy sau ${TIMEOUT}s"
    docker compose logs db | tail -20
    exit 1
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  printf "."
done
echo ""
log_ok "Database healthy"

log_info "Chờ backend (FastAPI) healthy..."
TIMEOUT=120
ELAPSED=0
until docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" &>/dev/null; do
  if [ $ELAPSED -ge $TIMEOUT ]; then
    log_error "Backend không healthy sau ${TIMEOUT}s. Xem logs:"
    docker compose logs backend | tail -30
    exit 1
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  printf "."
done
echo ""
log_ok "Backend healthy tại http://localhost:8000"

# =============================================================================
# BƯỚC 3 — Migration
# =============================================================================
log_section "Bước 3 — Chạy Database Migration"

log_info "Chạy Alembic migrations..."
docker compose exec -T backend uv run alembic upgrade head
log_ok "Migration hoàn tất"

# =============================================================================
# BƯỚC 4 — Seed dữ liệu
# =============================================================================
log_section "Bước 4 — Seed dữ liệu"

# Kiểm tra bảng modules có data chưa — chỉ seed nếu rỗng
MODULE_COUNT=$(docker compose exec -T db psql -U postgres -d ai_learning -tAc "SELECT COUNT(*) FROM modules;" 2>/dev/null | tr -d '[:space:]' || echo "0")
if [ "$MODULE_COUNT" = "0" ]; then
  log_info "Seed curriculum (modules, topics, questions)..."
  docker compose exec -T backend uv run python scripts/seed.py 2>&1 && log_ok "Seed curriculum hoàn tất" \
    || log_warn "seed.py thất bại — bỏ qua, tiếp tục"
else
  log_ok "Curriculum đã có sẵn (${MODULE_COUNT} module) — bỏ qua seed"
fi

# Kiểm tra bảng lectures có data chưa — chỉ seed nếu rỗng
LECTURE_COUNT=$(docker compose exec -T db psql -U postgres -d ai_learning -tAc "SELECT COUNT(*) FROM lectures;" 2>/dev/null | tr -d '[:space:]' || echo "0")
if [ "$LECTURE_COUNT" = "0" ]; then
  log_info "Seed bài giảng CS231n..."
  docker compose exec -T backend uv run python scripts/seed_lectures.py 2>&1 && log_ok "Seed bài giảng hoàn tất" \
    || log_warn "seed_lectures.py thất bại — bỏ qua (có thể không có data/CS231n/)"
else
  log_ok "Lectures đã có sẵn (${LECTURE_COUNT} bài) — bỏ qua seed"
fi

# =============================================================================
# BƯỚC 5 — Kiểm tra data trong container
# =============================================================================
log_section "Bước 5 — Kiểm tra data trong backend"

log_info "Kiểm tra thư mục /app/data trong container..."
docker compose exec -T backend python - <<'EOF'
import os, json

data_path = "/app/data"
cs231n_path = "/app/data/CS231n"

print(f"  data/ exists: {os.path.exists(data_path)}")

if os.path.exists(cs231n_path):
    videos = [f for f in os.listdir(f"{cs231n_path}/videos") if f.endswith(".mp4")] if os.path.exists(f"{cs231n_path}/videos") else []
    transcripts = os.listdir(f"{cs231n_path}/transcripts") if os.path.exists(f"{cs231n_path}/transcripts") else []
    toc = os.listdir(f"{cs231n_path}/ToC_Summary") if os.path.exists(f"{cs231n_path}/ToC_Summary") else []
    print(f"  CS231n/videos:      {len(videos)} files .mp4")
    print(f"  CS231n/transcripts: {len(transcripts)} files")
    print(f"  CS231n/ToC_Summary: {len(toc)} files")
else:
    print("  [WARN] CS231n/ không tồn tại trong container")

for f in ["modules.json", "topics.json", "question_bank.json"]:
    path = f"{data_path}/{f}"
    if os.path.exists(path):
        data = json.load(open(path))
        print(f"  {f}: {len(data)} records")
    else:
        print(f"  [WARN] {f} không tồn tại")
EOF

# =============================================================================
# HOÀN TẤT
# =============================================================================
log_section "Hoàn tất!"

echo -e ""
echo -e "  ${GREEN}Frontend:${NC}  http://localhost:3000"
echo -e "  ${GREEN}Backend:${NC}   http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}  http://localhost:8000/docs"
echo -e "  ${GREEN}Health:${NC}    http://localhost:8000/health"
echo -e ""
echo -e "  Xem logs:   ${YELLOW}docker compose logs -f backend${NC}"
echo -e "  Dừng app:   ${YELLOW}docker compose down${NC}"
echo -e ""
