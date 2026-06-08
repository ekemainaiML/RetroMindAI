# GitHub Secrets — Required Configuration

## Deploy Secrets (Production)

| Secret | Description | Required |
|--------|-------------|:--------:|
| `ORACLE_HOST` | Oracle Cloud VM public IP or hostname | Yes |
| `ORACLE_USER` | SSH username (e.g., `ubuntu`) | Yes |
| `ORACLE_SSH_KEY` | Private SSH key for deployment (PEM format) | Yes |
| `DOMAIN` | Production domain (e.g., `retromind.ai`) | Yes |

## Application Secrets (Set in .env.prod on the server)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | |
| `JWT_SECRET` | JWT signing secret (64+ char random) | |
| `ADMIN_API_KEY` | Admin API key for privileged operations | |
| `ENCRYPTION_KEY` | Base64-encoded 32-byte key for AES-256 encryption | |
| `SENTRY_DSN` | Sentry error tracking DSN (optional) | |
| `OPENAI_API_KEY` | OpenAI API key (optional) | |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | |
| `FRONTEND_URL` | Frontend URL for CORS | `https://retromind.ai` |
| `R2_ENDPOINT` | S3-compatible storage endpoint | |
| `R2_ACCESS_KEY` | S3 access key | |
| `R2_SECRET_KEY` | S3 secret key | |

## Adding Secrets

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with its value

## Rotation Policy

- `ORACLE_SSH_KEY`: Rotate every 6 months
- `JWT_SECRET`: Rotate if compromised
- `ENCRYPTION_KEY`: Rotate yearly (requires data re-encryption)
- API keys (OpenAI, Anthropic): Rotate every 90 days
