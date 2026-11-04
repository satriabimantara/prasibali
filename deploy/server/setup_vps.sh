#!/usr/bin/env bash
# One-time VPS setup for PrasiBali (Ubuntu 24.04/26.04, run as root; safe to run again).
#
#   scp deploy/server/setup_vps.sh root@prasibali.tech:
#   ssh root@prasibali.tech "bash setup_vps.sh"
#
# What it does:
#   1. system update, time zone Asia/Makassar, 4 GB swap (KVM 1 has 4 GB RAM)
#   2. Docker Engine + Compose plugin (Docker's apt repo; Ubuntu's own packages if the repo lacks this release)
#   3. UFW firewall: OpenSSH, 80/tcp, 443/tcp, 443/udp
#   4. user `deploy` (docker group) with root's SSH keys; SSH by key only (no passwords)
#   5. git deploy target: bare repo ~deploy/prasibali.git whose post-receive hook checks out master into
#      ~deploy/prasibali and starts deploy/server/deploy.sh in the background
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
SWAP_SIZE="${SWAP_SIZE:-4G}"
HOME_DIR="/home/${DEPLOY_USER}"
APP_DIR="${HOME_DIR}/prasibali"
REPO_DIR="${HOME_DIR}/prasibali.git"
export DEBIAN_FRONTEND=noninteractive

step() { printf '\n==> %s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run as root: ssh root@prasibali.tech \"bash setup_vps.sh\"" >&2; exit 1; }
. /etc/os-release
echo "OS: ${PRETTY_NAME} (${VERSION_CODENAME})"

step "1/5 System update, time zone, swap"
apt-get update -q
apt-get -y -q upgrade
apt-get install -y -q ca-certificates curl git ufw openssl
timedatectl set-timezone Asia/Makassar
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
    fallocate -l "${SWAP_SIZE}" /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=10' > /etc/sysctl.d/99-prasibali.conf
sysctl -q --system
free -h

step "2/5 Docker Engine + Compose"
if docker compose version >/dev/null 2>&1; then
    echo "Docker already installed: $(docker --version)"
else
    install -m 0755 -d /etc/apt/keyrings
    if curl -fsSI "https://download.docker.com/linux/ubuntu/dists/${VERSION_CODENAME}/Release" >/dev/null; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -q
        apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
        echo "Docker's repository has no '${VERSION_CODENAME}' yet: using Ubuntu's packages."
        apt-get install -y -q docker.io docker-compose-v2 docker-buildx
    fi
    systemctl enable --now docker
fi
docker --version
docker compose version

step "3/5 Firewall (UFW)"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw allow 443/udp >/dev/null
ufw --force enable >/dev/null
ufw status

step "4/5 User ${DEPLOY_USER} and SSH by key only"
id "${DEPLOY_USER}" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "${DEPLOY_USER}"
usermod -aG docker "${DEPLOY_USER}"
install -d -m 700 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "${HOME_DIR}/.ssh"
if [ -s /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys "${HOME_DIR}/.ssh/authorized_keys"
    chown "${DEPLOY_USER}:${DEPLOY_USER}" "${HOME_DIR}/.ssh/authorized_keys"
    chmod 600 "${HOME_DIR}/.ssh/authorized_keys"
    # 00- so it wins over cloud-init's 50-cloud-init.conf (sshd keeps the first value it reads).
    cat > /etc/ssh/sshd_config.d/00-prasibali.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
    sshd -t
    systemctl reload ssh 2>/dev/null || systemctl reload sshd
    echo "SSH: key login only (root and ${DEPLOY_USER}); password login disabled."
else
    echo "WARNING: /root/.ssh/authorized_keys is empty; password login left unchanged." >&2
fi

step "5/5 Git deploy target"
install -d -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "${APP_DIR}" "${APP_DIR}/models" "${APP_DIR}/backups"
if [ ! -d "${REPO_DIR}" ]; then
    runuser -u "${DEPLOY_USER}" -- git init -q --bare "${REPO_DIR}"
    runuser -u "${DEPLOY_USER}" -- git --git-dir="${REPO_DIR}" symbolic-ref HEAD refs/heads/master
fi
cat > "${REPO_DIR}/hooks/post-receive" <<EOF
#!/bin/sh
# Installed by deploy/server/setup_vps.sh. On a push to master: check the commit out into ${APP_DIR}
# (untracked .env, models/ and backups/ are never touched) and start the deploy in the background, so a dropped
# SSH connection does not stop a long image build.
set -eu
APP_DIR="${APP_DIR}"
REPO_DIR="${REPO_DIR}"
while read -r old new ref; do
    if [ "\$ref" != "refs/heads/master" ]; then
        echo "Only master is deployed; ignoring \$ref."
        continue
    fi
    if [ "\$new" = "0000000000000000000000000000000000000000" ]; then
        echo "master was deleted; nothing to deploy."
        continue
    fi
    git --git-dir="\$REPO_DIR" --work-tree="\$APP_DIR" checkout -q -f master
    echo "Checked out \$(echo "\$new" | cut -c1-7) into \$APP_DIR"
    unset GIT_DIR GIT_WORK_TREE
    setsid nohup bash "\$APP_DIR/deploy/server/deploy.sh" "\$new" >> "\$APP_DIR/deploy.log" 2>&1 < /dev/null &
    echo "Deploy started in the background. Follow it with:"
    echo "  ssh ${DEPLOY_USER}@prasibali.tech tail -f prasibali/deploy.log"
done
EOF
chmod 755 "${REPO_DIR}/hooks/post-receive"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${REPO_DIR}" "${APP_DIR}"

step "Done"
cat <<EOF
Next steps (docs/deploy_hostinger.md):
  - from the laptop:  ssh ${DEPLOY_USER}@prasibali.tech "echo ok"      (must work before you log out as root)
  - upload the model bundle to ${APP_DIR}/models
  - git remote add prod ${DEPLOY_USER}@prasibali.tech:prasibali.git && git push prod master
EOF
