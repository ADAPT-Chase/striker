#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/striker/health.log"
TS="$(date -u '+[%Y-%m-%d %H:%M:%S UTC]')"

DOCKER_OK=1
DF_OK=1
DB_OK=1
DISK="unknown"
MEM="unknown"
FIXES=()

# Docker containers
if command -v docker >/dev/null 2>&1; then
  CONTAINERS=$(sudo docker ps --format '{{.Names}}' 2>/dev/null | tr '\n' ' ' || true)
  if [[ -z "$CONTAINERS" ]]; then
    DOCKER_OK=0
    FIXES+=("docker-empty")
  fi
else
  DOCKER_OK=0
  FIXES+=("docker-missing")
fi

# Dragonfly
if command -v redis-cli >/dev/null 2>&1; then
  if ! redis-cli -p 6380 PING >/dev/null 2>&1; then
    DF_OK=0
    FIXES+=("dragonfly-down")
  fi
else
  DF_OK=0
  FIXES+=("redis-cli-missing")
fi

# Brain DB
if [[ ! -f "$HOME/striker/brain/striker.db" ]]; then
  DB_OK=0
  FIXES+=("brain-db-missing")
fi

# Disk / memory
DISK=$(df -h / | awk 'END {print $5 " used, " $4 " free"}')
MEM=$(free -h | awk '/Mem:/ {print $7 " avail of " $2}')

# Self-heal attempts
if [[ $DOCKER_OK -eq 0 ]]; then
  sudo docker compose -f "$HOME/firecrawl/docker-compose.yaml" up -d >/dev/null 2>&1 || true
  sudo docker start dragonfly >/dev/null 2>&1 || true
fi

if [[ $DF_OK -eq 0 ]]; then
  sudo docker start dragonfly >/dev/null 2>&1 || true
fi

# Re-check after fixes
POST_DOCKER=$(sudo docker ps --format '{{.Names}}' 2>/dev/null | tr '\n' ' ' || true)
POST_DF=$(redis-cli -p 6380 PING 2>/dev/null || true)

STATUS="OK"
if [[ -z "$POST_DOCKER" ]] || [[ "$POST_DF" != "PONG" ]] || [[ $DB_OK -eq 0 ]]; then
  STATUS="ISSUE"
fi

echo "$TS Health $STATUS — docker: ${POST_DOCKER:-none} | dragonfly: ${POST_DF:-down} | disk: $DISK | mem: $MEM | brain.db: $( [[ -f "$HOME/striker/brain/striker.db" ]] && echo present || echo missing ) | fixes: ${FIXES[*]:-none}" >> "$LOG"

echo "$STATUS"
