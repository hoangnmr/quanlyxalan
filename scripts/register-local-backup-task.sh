#!/usr/bin/env bash
# Register a daily backup job with launchd (macOS equivalent of the former
# Windows Scheduled Task).
set -euo pipefail

TIME="${1:-02:00}"
HOUR="${TIME%%:*}"
MINUTE="${TIME##*:}"
HOUR=$((10#$HOUR))
MINUTE=$((10#$MINUTE))

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo "Khong tim thay virtual environment: $PYTHON" >&2
    exit 1
fi

LABEL="com.cvf.kbcv.daily-backup"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
mkdir -p "$(dirname "$PLIST")"
mkdir -p "$PROJECT_ROOT/data/backups"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>scripts/backup_local.py</string>
        <string>--prune</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_ROOT}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$(dirname "$(command -v pg_dump)"):/usr/bin:/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${PROJECT_ROOT}/data/backups/backup.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_ROOT}/data/backups/backup.err.log</string>
</dict>
</plist>
PLIST_EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Da dang ky ${LABEL} luc ${TIME}."
echo "Go bo: launchctl bootout gui/$(id -u)/${LABEL} && rm ${PLIST}"
