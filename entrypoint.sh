#!/bin/bash
set -e

# Clean up old state
rm -rf /homeless-shelter /workspace/active_repo

# Copy the repo and assign ownership
cp -a /workspace/readonly_repo /workspace/active_repo

# Delete any host-machine caches that accidentally got copied over
rm -rf /workspace/active_repo/backend/.devenv
rm -rf /workspace/active_repo/backend/.direnv
rm -rf /workspace/active_repo/.direnv

chown -R devuser:devuser /workspace/active_repo
chmod -R u+rwX /workspace/active_repo
# Create a valid runtime directory for devenv/postgres
mkdir -p /run/user/1000
chown devuser:devuser /run/user/1000

# 3. Switch to the unprivileged user and start the environment
cd /workspace/active_repo
exec su devuser -c '
    export HOME=/home/devuser
    export USER=devuser
    export XDG_RUNTIME_DIR=/run/user/1000
    source /root/.nix-profile/etc/profile.d/nix.sh
    
    direnv allow .
    direnv exec . code-server --bind-addr 0.0.0.0:8081 --auth none
'