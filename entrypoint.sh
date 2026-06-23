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

# --- NEW: Ephemeral Skills Setup ---
# Create the .claude directory for devuser
mkdir -p /home/devuser/.claude

# Copy the skills over (if the readonly directory exists and isn't empty)
if [ -d "/workspace/readonly_skills" ] && [ "$(ls -A /workspace/readonly_skills)" ]; then
    rsync -rl /workspace/readonly_skills/ /home/devuser/.claude/
fi

# Ensure devuser owns their claude configuration
chown -R devuser:devuser /home/devuser/.claude

# --- Existing Execution Block ---
cd /workspace/active_repo
export HOME=/home/devuser
export USER=devuser
export XDG_RUNTIME_DIR=/run/user/1000

# Switch to devuser and execute
exec su - devuser -c '
  source /home/devuser/.nix-profile/etc/profile.d/nix.sh
  direnv allow admin
  direnv allow backend
  exec code-server --bind-addr 0.0.0.0:${CODE_SERVER_PORT:-8081} --auth none
'