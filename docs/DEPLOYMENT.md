# Deployment

## Local (Docker Compose)

```bash
# Start all services
docker compose -f deploy/docker-compose.demo.yml up -d

# Start without CPU TTS
docker compose -f deploy/docker-compose.demo.yml up -d gateway asr tts-gpu surya

# Start CPU TTS only (profile)
docker compose -f deploy/docker-compose.demo.yml --profile cpu-tts up -d
```

## Demo GPU VM (RTX 3090)

### Prerequisites

- Docker + NVIDIA Container Toolkit
- Clone repo: `git clone git@github.com:smykov/ai-services.git /opt/ecosystem-ai-services`

### systemd Service

```bash
cp deploy/ai-services.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ai-services.service
```

### Manual

```bash
cd /opt/ecosystem-ai-services
docker compose -f deploy/docker-compose.demo.yml up -d
```

## CI/CD Pipeline

1. Push tag `v*` triggers GitHub Actions
2. Build matrix: all 5 services → `ghcr.io/ecosystem/{service}:v*`
3. Deploy job (self-hosted runner):
   - SSH jump via the hypervisor host → GPU VM
   - `docker compose pull && up -d`

### Required Secrets

| Secret | Description |
|--------|-------------|
| `PROXMOX_HOST` | SSH jump host, e.g. `root@<proxmox-host>` |
| `VM110_HOST` | Target VM, e.g. `root@<gpu-vm>` |
| `DEMO_SSH_KEY` | Private key for SSH auth |

## Production (Cloud)

```bash
export IMAGE_TAG=v1.2.3
export MINIO_ACCESS_KEY=<secret>
export MINIO_SECRET_KEY=<secret>
export AI_API_KEYS=key1,key2
export AI_MCP_BEARER_TOKEN=<token>

docker compose -f deploy/docker-compose.cloud.yml up -d
```
