#! /usr/bin/bash

source .env

if [ -z "${WORKERS+x}" ]; then 
  WORKERS=4
fi

if [ -z "${HOST+x}" ]; then 
  HOST=127.0.0.1 
fi

if [ -z "${PORT+x}" ]; then 
  PORT=8000 
fi

if [ -z "${CLOUDFLARE_TOKEN+x}" ]; then
  echo "WARNING: CLOUDFLARE_TOKEN not set, will not be using cloudflare."
else
  cloudflared tunnel run --token $CLOUDFLARE_TOKEN --url $HOST:$PORT &
fi

uv run uvicorn app.main:app \
  --host $HOST \
  --port $PORT \
  --workers $WORKERS \
