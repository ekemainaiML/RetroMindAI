#!/bin/bash
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 retromind.example.com admin@example.com"
    exit 1
fi

if [ -z "$EMAIL" ]; then
    echo "Error: email is required for Let's Encrypt"
    exit 1
fi

echo "=== Provisioning RetroMind AI on Oracle Cloud Free Tier ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to re-login for group changes."
fi

if ! docker compose version &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

REPO_DIR="/app/retromind"
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning repository..."
    sudo mkdir -p "$REPO_DIR"
    sudo git clone https://github.com/ekemainaiML/RetroMindAI.git "$REPO_DIR"
    sudo chown -R "$USER:$USER" "$REPO_DIR"
fi

cd "$REPO_DIR"

if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
DOMAIN=$DOMAIN
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
NEO4J_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
ADMIN_API_KEY=rm_admin_$(openssl rand -hex 32)
OCI_REGION=eu-frankfurt-1
OCI_NAMESPACE=
OCI_ACCESS_KEY=
OCI_SECRET_KEY=
ENABLE_CAD_EXPORT=true
FREECAD_HOST=http://freecad-worker:8100
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
OPENAI_API_KEY=
SENTRY_DSN=
WORKSHOP_ID=default
EOF
    echo "Created .env — edit it to add your actual secrets"
fi

echo "Obtaining SSL certificate..."
docker run --rm \
    -v certbot_www:/var/www/certbot \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d "$DOMAIN" \
    --non-interactive --agree-tos \
    --email "$EMAIL" || echo "WARNING: Certbot failed. Run manually: sudo certbot certonly --standalone -d $DOMAIN"

mkdir -p backend/uploads

echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "=== Setup complete ==="
echo "Admin API key: $(grep ADMIN_API_KEY .env | cut -d= -f2)"
echo "Visit: https://$DOMAIN"
echo ""
echo "Next steps:"
echo "  1. Edit /app/retromind/.env with your real secrets"
echo "  2. Copy it to /app/.env.prod for CI/CD deployment"
echo "  3. Set GitHub Actions secrets: ORACLE_HOST, ORACLE_USER, ORACLE_SSH_KEY"
