#!/usr/bin/env bash
#
# Deploy QUANLYXALAN to production (ttport.vn/quanlyxalan).
#
# Strategy: build a tarball locally from the current commit, upload it, and
# extract it over the app directory on the server.
#
#   ./scripts/deploy.sh              # deploy HEAD
#   ./scripts/deploy.sh --dirty      # allow uncommitted changes (uses worktree)
#   ./scripts/deploy.sh --dry-run    # build the tarball, skip upload
#
# Extraction overwrites only what the archive contains, so runtime state on the
# server (.env, .venv/, data/) survives untouched. Files deleted from the repo
# are NOT removed from the server -- use --prune-cache for stale bytecode, or
# clean up by hand for anything larger.
#
set -euo pipefail

SSH_HOST="${SSH_HOST:-ttport}"
APP_DIR="${APP_DIR:-/var/www/ttport/quanlyxalan}"
SERVICE="${SERVICE:-quanlyxalan}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8002/}"
PUBLIC_URL="${PUBLIC_URL:-https://ttport.vn/quanlyxalan/}"
REMOTE_BACKUPS="${REMOTE_BACKUPS:-/var/www/ttport/backups/quanlyxalan}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DIRTY=0; DRY_RUN=0; PRUNE_CACHE=0
for arg in "$@"; do
  case "$arg" in
    --dirty)       DIRTY=1 ;;
    --dry-run)     DRY_RUN=1 ;;
    --prune-cache) PRUNE_CACHE=1 ;;
    -h|--help)     sed -n '2,18p' "$0" | sed 's|^# \?||'; exit 0 ;;
    *) echo "Tham số không hợp lệ: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preflight --
log "Kiểm tra trước khi deploy"

command -v git >/dev/null || die "Không tìm thấy git."
git rev-parse --git-dir >/dev/null 2>&1 || die "Không phải git repository."

if [[ -n "$(git status --porcelain)" ]]; then
  if [[ $DIRTY -eq 0 ]]; then
    git status --short
    die "Working tree có thay đổi chưa commit. Commit trước, hoặc chạy với --dirty."
  fi
  warn "Deploy kèm thay đổi chưa commit (--dirty)."
fi

COMMIT="$(git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
STAMP="$(date +%Y%m%d-%H%M%S)"
RELEASE="${COMMIT}-${STAMP}"

if [[ $DRY_RUN -eq 0 ]]; then
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" true \
    || die "Không SSH được tới '$SSH_HOST'. Kiểm tra ~/.ssh/config và SSH key."

  # Warn when the server is about to move backwards or sideways.
  if git remote get-url origin >/dev/null 2>&1; then
    git fetch -q origin "$BRANCH" 2>/dev/null || true
    if ! git merge-base --is-ancestor HEAD "origin/$BRANCH" 2>/dev/null; then
      warn "HEAD chưa được push lên origin/$BRANCH. Server sẽ chạy code chưa có trên GitHub."
    fi
  fi
fi

# -------------------------------------------------------------------- build --
DIST="$REPO_ROOT/dist"
TARBALL="$DIST/quanlyxalan-${RELEASE}.tar.gz"
mkdir -p "$DIST"

log "Đóng gói release $RELEASE (nhánh $BRANCH)"

if [[ $DIRTY -eq 1 ]]; then
  # Archive tracked files as they exist in the worktree, honouring .gitignore.
  git ls-files -z --cached --exclude-standard \
    | tar --null -czf "$TARBALL" --files-from=-
else
  git archive --format=tar HEAD | gzip -9 > "$TARBALL"
fi

[[ -s "$TARBALL" ]] || die "Đóng gói thất bại: tarball rỗng."

# The server needs these to boot; a missing one means a broken archive.
for required in backend/app.py frontend/index.html alembic.ini backend/requirements.txt; do
  tar -tzf "$TARBALL" | grep -qx "$required" \
    || die "Tarball thiếu '$required' — huỷ deploy."
done

log "Tarball: $TARBALL ($(du -h "$TARBALL" | cut -f1))"

if [[ $DRY_RUN -eq 1 ]]; then
  log "--dry-run: dừng tại đây, không upload."
  exit 0
fi

# ------------------------------------------------------------------- upload --
log "Upload lên $SSH_HOST"
scp -q "$TARBALL" "$SSH_HOST:/tmp/quanlyxalan-${RELEASE}.tar.gz"

# ------------------------------------------------------------------- deploy --
log "Giải nén và khởi động lại trên server"

ssh "$SSH_HOST" bash -euo pipefail -s <<REMOTE
APP_DIR="$APP_DIR"
SERVICE="$SERVICE"
RELEASE="$RELEASE"
HEALTH_URL="$HEALTH_URL"
REMOTE_BACKUPS="$REMOTE_BACKUPS"
KEEP_BACKUPS="$KEEP_BACKUPS"
PRUNE_CACHE="$PRUNE_CACHE"
TARBALL="/tmp/quanlyxalan-\${RELEASE}.tar.gz"

say() { printf '    \033[0;36m%s\033[0m\n' "\$*"; }

[[ -d "\$APP_DIR" ]]  || { echo "Không tìm thấy \$APP_DIR"; exit 1; }
[[ -f "\$APP_DIR/.env" ]] || { echo "Thiếu \$APP_DIR/.env — huỷ deploy."; exit 1; }
mkdir -p "\$REMOTE_BACKUPS"

# --- backup code + database trước khi đổi bất cứ thứ gì -----------------
say "Backup code hiện tại"
tar -czf "\$REMOTE_BACKUPS/code-\${RELEASE}.tar.gz" \
    -C "\$APP_DIR" --exclude=.venv --exclude=data --exclude=.git . 2>/dev/null

say "Backup database"
set -a; . "\$APP_DIR/.env"; set +a
# DATABASE_URL -> libpq URL (drop the SQLAlchemy +psycopg driver suffix)
PG_URL="\${DATABASE_URL/+psycopg/}"
if ! pg_dump "\$PG_URL" | gzip > "\$REMOTE_BACKUPS/db-\${RELEASE}.sql.gz"; then
  echo "pg_dump thất bại — huỷ deploy."; exit 1
fi

# --- giải nén đè -------------------------------------------------------
say "Giải nén release \$RELEASE"
if [[ "\$PRUNE_CACHE" == "1" ]]; then
  find "\$APP_DIR" -path "\$APP_DIR/.venv" -prune -o -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
fi
tar -xzf "\$TARBALL" -C "\$APP_DIR"

# --- dependencies ------------------------------------------------------
say "Đồng bộ dependencies"
"\$APP_DIR/.venv/bin/pip" install -q --upgrade -r "\$APP_DIR/backend/requirements.txt"

# --- migrations --------------------------------------------------------
say "Chạy migration"
cd "\$APP_DIR"
if ! .venv/bin/alembic upgrade head; then
  echo "Migration thất bại — huỷ deploy. DB backup: \$REMOTE_BACKUPS/db-\${RELEASE}.sql.gz"
  exit 1
fi

# --- restart -----------------------------------------------------------
say "Khởi động lại \$SERVICE"
systemctl restart "\$SERVICE"

# --- health check ------------------------------------------------------
for i in \$(seq 1 15); do
  CODE=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "\$HEALTH_URL" || echo 000)
  [[ "\$CODE" == "200" ]] && break
  sleep 2
done

if [[ "\$CODE" != "200" ]]; then
  echo "Health check thất bại (HTTP \$CODE). Nhật ký gần nhất:"
  journalctl -u "\$SERVICE" -n 30 --no-pager
  echo
  echo "Rollback code:"
  echo "  tar -xzf \$REMOTE_BACKUPS/code-\${RELEASE}.tar.gz -C \$APP_DIR && systemctl restart \$SERVICE"
  echo "Rollback database:"
  echo "  gunzip -c \$REMOTE_BACKUPS/db-\${RELEASE}.sql.gz | psql '\$PG_URL'"
  exit 1
fi
say "Health check OK (HTTP 200)"

# --- dọn dẹp -----------------------------------------------------------
rm -f "\$TARBALL"
ls -1t "\$REMOTE_BACKUPS"/code-*.tar.gz 2>/dev/null | tail -n +\$((KEEP_BACKUPS+1)) | xargs -r rm -f
ls -1t "\$REMOTE_BACKUPS"/db-*.sql.gz  2>/dev/null | tail -n +\$((KEEP_BACKUPS+1)) | xargs -r rm -f
REMOTE

# -------------------------------------------------------------- verify --
log "Kiểm tra công khai"
CODE="$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 15 "$PUBLIC_URL" || echo 000)"
[[ "$CODE" == "200" ]] || die "$PUBLIC_URL trả về HTTP $CODE"

# Giữ lại 5 tarball gần nhất ở máy local.
ls -1t "$DIST"/quanlyxalan-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f

log "Deploy thành công: $RELEASE → $PUBLIC_URL"
