#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <repo-url> <registration-token> [runner-name] [labels]"
  exit 1
fi

REPO_URL="$1"
REG_TOKEN="$2"
RUNNER_NAME="${3:-$(hostname)-gha-runner}"
RUNNER_LABELS="${4:-self-hosted,linux,x64,aws,ec2}"
RUNNER_ROOT="/runner"
RUNNER_DIR="${RUNNER_ROOT}/actions-runner"
RUNNER_VERSION="2.334.0"
RUNNER_ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_ARCHIVE}"

sudo mkdir -p "${RUNNER_DIR}"
sudo chown -R runner:runner "${RUNNER_ROOT}"

sudo -u runner bash <<EOF
set -euo pipefail
cd "${RUNNER_DIR}"
if [ ! -f "./config.sh" ]; then
  curl -fsSL -o "${RUNNER_ARCHIVE}" "${RUNNER_URL}"
  tar xzf "./${RUNNER_ARCHIVE}"
fi

./config.sh \
  --url "${REPO_URL}" \
  --token "${REG_TOKEN}" \
  --name "${RUNNER_NAME}" \
  --labels "${RUNNER_LABELS}" \
  --work "_work" \
  --unattended \
  --replace
EOF

cd "${RUNNER_DIR}"
sudo ./svc.sh install runner
sudo ./svc.sh start
sudo ./svc.sh status
