#!/bin/bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ./setup_dnsmasq_autoupdate.sh [username]"
  exit 1
fi

TARGET_USER="${1:-${SUDO_USER:-nikhil}}"
HELPER_PATH="/usr/local/sbin/wifi-dnsmasq-apply"
SUDOERS_FILE="/etc/sudoers.d/wifi-dnsmasq"

echo "Configuring dnsmasq auto-update helper for user: ${TARGET_USER}"

cat > "${HELPER_PATH}" <<'EOF'
#!/bin/bash
set -euo pipefail

BLOCKLIST="/etc/dnsmasq.d/blocklist.conf"

if [[ "${1:-}" == "--clear" ]]; then
  rm -f "${BLOCKLIST}"
else
  SRC="$(readlink -f "${1:?temp blocklist file required}")"
  [[ "${SRC}" == /tmp/* ]] || { echo "Only /tmp source files are allowed"; exit 2; }
  install -o root -g root -m 0644 "${SRC}" "${BLOCKLIST}"
fi

systemctl restart dnsmasq
EOF

chown root:root "${HELPER_PATH}"
chmod 750 "${HELPER_PATH}"

echo "${TARGET_USER} ALL=(root) NOPASSWD: ${HELPER_PATH} *" > "${SUDOERS_FILE}"
chmod 440 "${SUDOERS_FILE}"

if ! visudo -cf "${SUDOERS_FILE}"; then
  echo "sudoers validation failed, removing ${SUDOERS_FILE}"
  rm -f "${SUDOERS_FILE}"
  exit 1
fi

echo "Done. Non-interactive dnsmasq updates are enabled for ${TARGET_USER}."
