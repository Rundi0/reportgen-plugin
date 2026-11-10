#!/usr/bin/env bash
# Bridge plugin settings to the CLI. Claude Code exports userConfig values
# (CLAUDE_PLUGIN_OPTION_*) to hooks only, not to Bash-tool commands, so persist
# them where the reportgen wrapper looks. No key configured -> leave the file
# alone, so a hand-written one keeps working.
set -euo pipefail
[ -n "${CLAUDE_PLUGIN_OPTION_API_KEY:-}" ] || exit 0

dir="${XDG_CONFIG_HOME:-$HOME/.config}/reportgen"
umask 077
mkdir -p "$dir"
url="${CLAUDE_PLUGIN_OPTION_URL:-}"
verify="${CLAUDE_PLUGIN_OPTION_VERIFY_TLS:-true}"
# report.lan serves a self-signed certificate, so it never verifies.
case "$url" in https://report.lan | https://report.lan/*) verify=false ;; esac
printf 'REPORTGEN_URL=%s\nREPORTGEN_API_KEY=%s\nREPORTGEN_VERIFY_TLS=%s\n' \
    "$url" "$CLAUDE_PLUGIN_OPTION_API_KEY" "$verify" > "$dir/.env"
chmod 600 "$dir/.env"
