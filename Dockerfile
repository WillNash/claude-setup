FROM ubuntu:latest

# 1. Install all system dependencies in one go
RUN apt-get update && \
    apt-get install -y \
        git curl xz-utils wget ca-certificates \
        nodejs npm direnv sudo && \
    rm -rf /var/lib/apt/lists/*

# 2. Prepare Nix config for a root container install
# Clearing build-users-group tells Nix not to look for the 'nixbld' daemon group.
RUN mkdir -p /etc/nix && \
    echo "build-users-group =" >> /etc/nix/nix.conf && \
    echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# 3. Install Nix in single-user mode
# Explicitly passing USER=root satisfies the script's environment checks
RUN USER=root curl -L https://nixos.org/nix/install | sh -s -- --no-daemon

# 4. Add Nix to the PATH for the rest of the build and runtime
ENV PATH="/root/.nix-profile/bin:$PATH"

# 5. Install devenv via Nix
RUN nix-env --install --attr devenv -f https://github.com/NixOS/nixpkgs/tarball/nixpkgs-unstable

# 6. Configure Direnv and Git defaults
RUN echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
RUN git config --global --add safe.directory '*' && \
    git config --global user.name "Claude Sandbox" && \
    git config --global user.email "claude@sandbox.local"

# 7. Install external tools
RUN curl -fsSL https://code-server.dev/install.sh | sh
RUN npm install -g @anthropic-ai/claude-code

# Set working directory
WORKDIR /workspace