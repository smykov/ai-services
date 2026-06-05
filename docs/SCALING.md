# Scaling

## Strategy

| Stage | Configuration |
|-------|--------------|
| **Demo** | 1 machine, all services (VM 110, RTX 3090) |
| **Staging** | 2 GPU servers (A10G) |
| **Production** | K8s cluster + GPU pool + CPU spot |

## GPU Workers

All 3 GPU workers (asr + tts-gpu + surya) fit on a single RTX 3090 (24 GB):

| Service | VRAM (idle) |
|---------|------------|
| asr (large-v3) | 3.1 GB |
| tts-gpu (XTTS-v2) | 2.0 GB |
| surya | 1.5 GB |
| CUDA overhead | 0.5 GB |
| **Total** | **7.1 GB / 24 GB** |

## CPU Scaling

- `tts-cpu` uses Piper TTS — CPU-only, horizontally scalable
- Enable via profile: `--profile cpu-tts`
- Route CPU TTS tasks to `tts:cpu:queue` for cheap scale

## Cloud GPU

| Provider | GPU | Approx Cost |
|----------|-----|------------|
| Hetzner | RTX 4000 / A100 | €0.50-2/hr |
| AWS | g5.xlarge (A10G) | $1.0+/hr |
| Vast.ai | Various | $0.1-0.3/hr |

## Queue

Redis Streams with consumer groups — each worker type forms its own group:

- `asr:queue` → `asr-workers`
- `tts:queue` → `tts-workers`
- `tts:cpu:queue` → `tts-cpu-workers`
- `surya:queue` → `surya-workers`

Add more workers per group for parallel processing (horizontal scale).
