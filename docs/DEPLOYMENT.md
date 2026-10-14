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

1. Push a `v*` tag (or run the workflow by hand) to trigger `Deploy`
2. Build matrix: all 6 services → `ghcr.io/<owner>/ai-services-{service}:v*` (used by the cloud compose)
3. Deploy job (self-hosted runner labelled `self-hosted, proxmox, linux`):
   - `ssh ai-services-vm`, then runs `deploy/deploy-demo.sh <sha>` on the VM: `git checkout <sha>`
     in `/opt/ecosystem-ai-services`, then `docker compose --profile gpu-workers up -d --build`
     from `deploy/`, then waits for `/health`

### Runner setup

No repository secrets. The runner user's `~/.ssh/config` defines the target, and the VM's
`/root/.ssh/authorized_keys` holds the runner's public key:

```
Host ai-services-vm
  HostName <gpu-vm>
  User root
  IdentityFile ~/.ssh/<runner key>
  StrictHostKeyChecking accept-new
```

## Production (Cloud)

```bash
export IMAGE_TAG=v1.2.3
export MINIO_ACCESS_KEY=<secret>
export MINIO_SECRET_KEY=<secret>
export AI_API_KEYS=key1,key2
export AI_MCP_BEARER_TOKEN=<token>

docker compose -f deploy/docker-compose.cloud.yml up -d
```
