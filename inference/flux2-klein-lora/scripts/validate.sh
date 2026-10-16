#!/usr/bin/env bash
set -Eeuo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root_dir=$(cd -- "$script_dir/.." && pwd)

for script in "$script_dir"/*.sh "$root_dir/entrypoint.sh"; do
  bash -n "$script"
done
python3 -m py_compile "$script_dir/smoke-test.py" "$root_dir"/app/*.py

temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/flux2-klein-lora-validate.XXXXXX")
trap 'rm -rf -- "$temp_dir"' EXIT
dry_run=$(
  NEBIUS_PROFILE=example \
  PROJECT_ID=project-example \
  IMAGE="registry.example/flux2-klein-lora@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" \
  HF_TOKEN_SECRET_SELECTOR=redacted \
  AUTH_TOKEN_SECRET_SELECTOR=redacted \
  STATE_DIR="$temp_dir/state" \
  "$script_dir/deploy-endpoint.sh" --dry-run
)
jq -e '
  .dry_run == true
  and .platform == "gpu-b200-sxm"
  and .auth == "token"
  and .preemptible == true
  and .pricing == "follows-spot-price"
  and .secrets == "configured; values and selectors redacted"
' <<<"$dry_run" >/dev/null

PYTHONPATH="$root_dir" python3 -m pytest -q "$root_dir/tests"
python3 -m ruff check "$root_dir/app" "$root_dir/tests" "$script_dir/smoke-test.py"
echo "shell, dry-run, Python unit, and lint validation passed"
