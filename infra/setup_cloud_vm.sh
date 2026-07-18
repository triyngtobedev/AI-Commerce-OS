#!/usr/bin/env bash
# Setup one-shot da VM na nuvem (Hetzner Cloud CX22/CX32)
#
# Execute NA VM (Ubuntu 22.04/24.04), como root ou com sudo:
#   curl -fsSL https://raw.githubusercontent.com/SEU_USUARIO/AI-Commerce-OS/main/infra/setup_cloud_vm.sh | bash
#   — ou, após clonar o repo:
#   sudo bash infra/setup_cloud_vm.sh
#
# O script instala Docker, clona o projeto e sobe o pipeline.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/SEU_USUARIO/AI-Commerce-OS.git}"
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-commerce-os}"
COMPOSE_FILE="infra/docker-compose.cloud.yml"

echo "=== AI-Commerce-OS — Setup da VM na nuvem ==="

if ! command -v docker &>/dev/null; then
  echo "→ Instalando Docker..."
  apt-get update
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME:-$VERSION}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  echo "✓ Docker instalado"
else
  echo "✓ Docker já instalado"
fi

if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "→ Clonando repositório em $INSTALL_DIR..."
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  echo "→ Atualizando repositório..."
  git -C "$INSTALL_DIR" pull --ff-only || true
fi

cd "$INSTALL_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠️  IMPORTANTE: edite $INSTALL_DIR/.env com suas chaves de API"
  echo "   nano $INSTALL_DIR/.env"
  echo ""
fi

# Gera PIPELINE_API_KEY se ainda não existir
if ! grep -q '^PIPELINE_API_KEY=.\+' .env 2>/dev/null; then
  KEY=$(openssl rand -hex 16)
  echo "PIPELINE_API_KEY=$KEY" >> .env
  echo "→ PIPELINE_API_KEY gerada automaticamente: $KEY"
  echo "   Copie essa chave para o .env do seu PC local!"
fi

# Firewall local (UFW) — complementa o firewall do painel Hetzner
PORT=$(grep -E '^PIPELINE_API_PORT=' .env 2>/dev/null | cut -d= -f2)
PORT="${PORT:-8000}"
if command -v ufw &>/dev/null; then
  echo "→ Configurando UFW (portas 22 e ${PORT})..."
  ufw allow 22/tcp
  ufw allow "${PORT}"/tcp
  ufw --force enable
  echo "✓ UFW ativo"
fi

echo "→ Construindo e iniciando pipeline (pode levar 5-10 min na primeira vez)..."
docker compose -f "$COMPOSE_FILE" up -d --build

PUBLIC_IP=$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "=== Setup concluído ==="
echo ""
echo "  API:  http://${PUBLIC_IP}:${PORT}/api/v1/health"
echo "  Docs: http://${PUBLIC_IP}:${PORT}/api/docs"
echo ""
echo "No seu PC, configure o .env local:"
echo "  CLOUD_API_URL=http://${PUBLIC_IP}:${PORT}"
echo "  CLOUD_API_KEY=<mesma PIPELINE_API_KEY da VM>"
echo ""
echo "Depois rode no PC:"
echo "  python scripts/cloud/gerar_video.py --topic \"Seu tema aqui\""
echo ""
echo "Confirme a porta ${PORT} no firewall do painel Hetzner (Firewalls → TCP ${PORT})."
