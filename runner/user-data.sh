#!/usr/bin/env bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  jq \
  unzip \
  tar \
  build-essential \
  apt-transport-https \
  software-properties-common

if ! id -u runner >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash runner
fi

mkdir -p /runner /runner/bin /runner/logs /runner/tmp /runner/bootstrap
chown -R runner:runner /runner

# Docker is required for GitHub Actions service containers and image builds.
apt-get install -y docker.io
systemctl enable docker
systemctl start docker
usermod -aG docker runner

# Node.js 20 for frontend workflow jobs.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y nodejs

# Python 3.12 for backend workflow jobs.
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.12 python3.12-venv python3-pip

# Terraform for infra workflow jobs.
curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(. /etc/os-release && echo "$VERSION_CODENAME") main" > /etc/apt/sources.list.d/hashicorp.list
apt-get update
apt-get install -y terraform

# AWS CLI v2 is used by deploy workflows.
cd /tmp
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install --update
rm -rf /tmp/aws /tmp/awscliv2.zip

cat >/runner/bootstrap/versions.txt <<'EOF'
Bootstrap completed.
EOF

{
  echo "docker=$(docker --version)"
  echo "node=$(node --version)"
  echo "npm=$(npm --version)"
  echo "python=$(python3.12 --version)"
  echo "pip=$(python3 -m pip --version)"
  echo "terraform=$(terraform version | head -n 1)"
  echo "aws=$(aws --version)"
} >>/runner/bootstrap/versions.txt

chown -R runner:runner /runner
