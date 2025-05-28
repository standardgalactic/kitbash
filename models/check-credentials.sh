#!/usr/bin/bash

curl -X POST https://models.github.ai/inference/chat/completions \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d '{"messages":[{"role":"user","content":"Test"}],"model":"xai/grok-3-mini"}'
