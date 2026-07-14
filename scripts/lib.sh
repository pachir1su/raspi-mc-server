#!/usr/bin/env bash
# Shared shell helpers for raspi-mc-server operational scripts.

# Validate and export a shell-compatible environment file when it exists.
load_env_file() {
  local envFile="${1:?environment file path is required}"
  [ -f "$envFile" ] || return 0

  # Validate in strict Bash first so failures retain the source file and line.
  local status=0
  bash -euo pipefail -c 'set -a; . "$1"; set +a' _ "$envFile" || status=$?
  if [ "$status" -ne 0 ]; then
    echo "!! Failed to load environment file: $envFile (exit $status)." >&2
    echo "   Fix the shell syntax at the file and line reported above." >&2
    return "$status"
  fi

  # Export validated values into the caller's environment.
  set -a
  # shellcheck disable=SC1090
  . "$envFile"
  set +a
}
