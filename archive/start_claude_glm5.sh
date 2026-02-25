#!/bin/bash

# Configuration
GLM5_API_KEY="b77de39782df4baeb4de1be7fe6b59eb.3YEACUTmbSsfY3aV"
PROXY_PORT=4000

echo "Checking for LiteLLM requirement..."
if ! python3 -m litellm --version &> /dev/null; then
    echo "Installing LiteLLM proxy (required for format translation)..."
    python3 -m pip install litellm
fi

# Stop any existing LiteLLM on this port
lsof -ti :$PROXY_PORT | xargs kill -9 2>/dev/null

# Start LiteLLM proxy in the background mapping Anthropic requests to GLM-5
echo "Starting LiteLLM API proxy to translate Claude Code requests into GLM-5 formats..."
python3 -m litellm --model openai/glm-5 \
        --api_base "https://open.bigmodel.cn/api/paas/v4/" \
        --api_key "$GLM5_API_KEY" \
        --port $PROXY_PORT > /tmp/litellm_proxy.log 2>&1 &
PROXY_PID=$!

# Wait for proxy to boot
sleep 2

if ps -p $PROXY_PID > /dev/null; then
   echo "✅ Proxy successfully mapping Anthropic API -> GLM-5 (PID $PROXY_PID)."
   echo ""
   echo "========================================="
   echo "To use Claude Code now, copy and paste the following commands into your terminal:"
   echo "========================================="
   echo ""
   echo "export ANTHROPIC_BASE_URL=\"http://0.0.0.0:$PROXY_PORT\""
   echo "export ANTHROPIC_AUTH_TOKEN=\"dummy_token\""
   echo "claude"
   echo ""
   echo "========================================="
   echo "To stop the proxy when you're done, run: kill $PROXY_PID"
else
   echo "❌ Failed to start LiteLLM proxy. Check logs at /tmp/litellm_proxy.log"
fi
