#!/usr/bin/env bash
set -euo pipefail

template_path="${1:?template path is required}"
output_path="${2:?output path is required}"

content="$(<"$template_path")"

mapfile -t placeholders < <(grep -o "__[A-Z0-9_][A-Z0-9_]*__" "$template_path" | sed 's/^__//; s/__$//' | sort -u)

for key in "${placeholders[@]}"; do
  if [ -z "${!key:-}" ]; then
    echo "Missing required environment variable: ${key}" >&2
    exit 2
  fi
  value="${!key}"
  content="${content//__${key}__/$value}"
done

if grep -q "__[A-Z0-9_][A-Z0-9_]*__" <<<"$content"; then
  echo "Unresolved template placeholders remain:" >&2
  grep -o "__[A-Z0-9_][A-Z0-9_]*__" <<<"$content" | sort -u >&2
  exit 3
fi

printf '%s\n' "$content" > "$output_path"

if command -v jq >/dev/null 2>&1; then
  jq empty "$output_path"
fi
