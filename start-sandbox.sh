#!/bin/bash

# 1. Define the repository you want to mount
TARGET_REPO=${1:-"$(pwd)/worldrugby-scrm"}
echo TARGET_REPO
# 2. Safety Check: Ensure the API key is set in your host environment
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable is not set."
    echo "Please set it first by running: export ANTHROPIC_API_KEY='your-actual-api-key'"
    exit 1
fi

# 3. Safety Check: Ensure the target directory actually exists
if [ ! -d "$TARGET_REPO" ]; then
    echo "❌ Error: The directory '$TARGET_REPO' does not exist."
    exit 1
fi

# Convert the repo path to an absolute path (Docker requires absolute paths for volume mounts)
TARGET_REPO_ABS=$(cd "$TARGET_REPO" && pwd)

echo "🚀 Starting Claude Sandbox..."
echo "🔒 Mounting read-only host directory: $TARGET_REPO_ABS"
echo "📂 Code will be safely copied to /workspace/active_repo inside the container."

# 4. Run the Docker container
docker run -it --rm \
  --name claude-sandbox \
  --network secure_net \
  -e http_proxy="http://proxy_guard:3128" \
  -e no_proxy="localhost,127.0.0.1,0.0.0.0" \
  -e https_proxy="http://proxy_guard:3128" \
  -v "$TARGET_REPO_ABS":/workspace/readonly_repo:ro \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  claude-sandbox-image \
  bash -c "cp -a /workspace/readonly_repo /workspace/active_repo && \
           cd /workspace/active_repo && \
           code-server --bind-addr 0.0.0.0:8080 --auth none"