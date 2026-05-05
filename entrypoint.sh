#!/bin/bash
set -e

# Clean up old state
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

# Make sure devuser has write permissions to the newly copied files
chmod -R u+rwX /workspace/active_repo

# Start the environment
cd /workspace/active_repo

export HOME=/home/devuser
export USER=devuser
export XDG_RUNTIME_DIR=/run/user/1000

# Use the correct Nix path for devuser
source /home/devuser/.nix-profile/etc/profile.d/nix.sh
    
direnv allow admin
direnv allow backend

# Execute code-server directly
exec code-server --bind-addr 0.0.0.0:8081 --auth none