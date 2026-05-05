#!/bin/bash
set -e

# Clean up old state (if the container was restarted)
rm -rf /workspace/active_repo

# Copy the repo using -r instead of -a
# (-r creates new files naturally owned by devuser, avoiding host UID conflicts)
cp -r /workspace/readonly_repo /workspace/active_repo

# Make sure devuser has write permissions to the newly copied files
chmod -R u+rwX /workspace/active_repo

# Aggressively delete ALL host-machine caches that got copied over
find /workspace/active_repo -type d -name ".devenv" -exec rm -rf {} +
find /workspace/active_repo -type d -name ".direnv" -exec rm -rf {} +
find /workspace/active_repo -type d -name ".direnv_cache" -exec rm -rf {} +

# Start the environment
cd /workspace/active_repo

export HOME=/home/devuser
export USER=devuser
export XDG_RUNTIME_DIR=/run/user/1000

# Use the correct Nix path for devuser
source /home/devuser/.nix-profile/etc/profile.d/nix.sh
    
direnv allow .

# We no longer need 'su' because we are already devuser. 
# Execute code-server directly.
exec direnv exec . code-server --bind-addr 0.0.0.0:8081 --auth none