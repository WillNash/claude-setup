# Use the official Ubuntu 24.04 LTS image
FROM ubuntu:24.04

# Prevent interactive prompts during apt package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    curl \
    xz-utils \
    git \
    nodejs \
    npm \
    direnv \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Tell Git to trust all directories, and set a default sandbox identity
RUN git config --global --add safe.directory '*' && \
    git config --global user.name "Claude Sandbox" && \
    git config --global user.email "claude@sandbox.local"
   
# Install code-server (Browser-based VS Code)
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install Claude Code via npm
RUN npm install -g @anthropic-ai/claude-code

# Pre-configure Nix before installing it:
# 1. Disable the multi-user build group requirement
# 2. Enable flakes and the new command-line interface
# 3. Trust the root user so devenv can utilize its binary caches
RUN mkdir -p /etc/nix && \
    echo "build-users-group =" >> /etc/nix/nix.conf && \
    echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf && \
    echo "trusted-users = root" >> /etc/nix/nix.conf

# Pre-create the /nix directory to bypass the installer's need for 'sudo', 
# then install Nix in single-user mode.
RUN mkdir -m 0755 /nix && \
    curl -L https://nixos.org/nix/install | sh -s -- --no-daemon

# Add Nix to the PATH so subsequent Docker build steps can use it
ENV PATH="/root/.nix-profile/bin:${PATH}"

# Install the exact patch version of devenv using Nix flakes
RUN nix profile install --accept-flake-config github:cachix/devenv/v1.3.1

# Configure the interactive bash environment:
# 1. Source Nix so its binaries are available in interactive shells
# 2. Hook direnv into bash
RUN echo 'source /root/.nix-profile/etc/profile.d/nix.sh' >> /root/.bashrc && \
    echo 'eval "$(direnv hook bash)"' >> /root/.bashrc

# Set up a working directory
WORKDIR /workspace

# Default to bash so the .bashrc hooks execute properly
CMD ["bash"]
# Create an unprivileged user for running Postgres and DevEnv securely,
# and hand over ownership of the entire Nix store so they can build packages.
RUN useradd -m -s /bin/bash devuser && \
    cp /root/.bashrc /home/devuser/.bashrc && \
    chown devuser:devuser /home/devuser/.bashrc && \
    chmod 755 /root && \
    chown -R devuser:devuser /nix