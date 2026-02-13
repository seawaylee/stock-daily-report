#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LABEL="com.stock_daily_report.after_close"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
LOG_DIR="${REPO_ROOT}/logs"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${LOG_DIR}"

cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd "${REPO_ROOT}" &amp;&amp; "${REPO_ROOT}/scripts/run_after_close.sh"</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>

  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>10</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>10</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>10</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>10</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>10</integer></dict>
  </array>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/after_close_scheduler.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/after_close_scheduler.err.log</string>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF

launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}"

echo "✅ Installed launchd job: ${LABEL}"
echo "Plist: ${PLIST_PATH}"
echo "Log out: ${LOG_DIR}/after_close_scheduler.out.log"
echo "Log err: ${LOG_DIR}/after_close_scheduler.err.log"
echo "Inspect: launchctl list | grep ${LABEL}"
