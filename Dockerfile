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

# 2. Create the unprivileged user FIRST
RUN useradd -m -s /bin/bash devuser

# 3. Pre-create the /nix folder and give devuser ownership BEFORE installing Nix
RUN mkdir -p /nix && chown devuser:devuser /nix

# 4. Switch to the new user. Every command after this line runs as devuser!
USER devuser
ENV USER=devuser
ENV HOME=/home/devuser

# 5. Install Nix. Because devuser owns /nix, it installs perfectly without root.
RUN curl -L https://nixos.org/nix/install | sh -s -- --no-daemon

# 6. Add Nix to the system PATH so Docker can find the 'nix' and 'devenv' commands
ENV PATH="/home/devuser/.nix-profile/bin:$PATH"

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
