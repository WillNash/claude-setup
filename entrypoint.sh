#!/bin/bash
set -e

# --- Existing Repo Setup ---
rm -rf /workspace/active_repo
mkdir -p /workspace/active_repo

# Copy the repo using rsync, explicitly EXCLUDING the restricted host caches
# -r means recursive, -l preserves symlinks
rsync -rl \
  --exclude='.devenv*' \
  --exclude='.direnv' \
  --exclude='.direnv_cache' \
  --exclude='.cache' \
  /workspace/readonly_repo/ /workspace/active_repo/

chown -R devuser:devuser /workspace/active_repo

## --- 2. Ephemeral Skills Setup ---
# Create the specific plugin directory that Claude Code expects
mkdir -p /home/devuser/.claude/plugins/wills-plugins

# First IF block (Fixed missing 'fi')
if [ -d "/workspace/readonly_plugin" ] && [ "$(ls -A /workspace/readonly_plugin)" ]; then
    rsync -rl /workspace/readonly_plugin/ /home/devuser/.claude/plugins/wills-plugins
fi

# Second IF block (Settings JSON)
if [ -f "/workspace/claude_settings/settings.json" ]; then  
    cp -r /workspace/claude_settings/settings.json /home/devuser/.claude/settings.json
fi

# 4. Ensure Claude Code can write/modify skills during this active session
chmod -R u+rwX /home/devuser/.claude
# Ensure devuser owns their claude configuration
chown -R devuser:devuser /home/devuser/.claude

# --- Environment Execution ---
cd /workspace/active_repo

export XDG_RUNTIME_DIR=/run/user/1000

# Load Nix
source /home/devuser/.nix-profile/etc/profile.d/nix.sh

# Trust the directories
direnv allow admin
direnv allow backend

# Execute code-server directly (replaces the current bash shell)
exec code-server --bind-addr 0.0.0.0:${CODE_SERVER_PORT:-8081} --auth none