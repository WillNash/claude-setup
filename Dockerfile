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
   
# Install code-server (Browser-based VS Code) globally
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install Claude Code via npm globally
RUN npm install -g @anthropic-ai/claude-code

# Create the unprivileged user FIRST
RUN useradd -m -s /bin/bash devuser

# Pre-create the /nix directory and give ownership to devuser
RUN mkdir -m 0755 /nix && \
    chown devuser:devuser /nix

# Pre-create necessary directories and assign ownership BEFORE switching users
RUN mkdir -p /workspace /run/user/1000 && \
    chown -R devuser:devuser /workspace /run/user/1000

    # Switch to the unprivileged user for all subsequent commands
USER devuser
WORKDIR /home/devuser

# Pre-configure Nix for devuser
RUN mkdir -p /home/devuser/.config/nix && \
    echo "experimental-features = nix-command flakes" >> /home/devuser/.config/nix/nix.conf

# Install Nix as the devuser in single-user mode
RUN curl -L https://nixos.org/nix/install | sh -s -- --no-daemon

# Add Nix to the PATH for the rest of the build process
ENV PATH="/home/devuser/.nix-profile/bin:${PATH}"

# Install the exact patch version of devenv using Nix flakes
RUN nix profile install --accept-flake-config github:cachix/devenv/v1.3.1

# Configure the interactive bash environment for devuser
RUN echo 'source /home/devuser/.nix-profile/etc/profile.d/nix.sh' >> /home/devuser/.bashrc && \
    echo 'eval "$(direnv hook bash)"' >> /home/devuser/.bashrc

# Set up the shared workspace directory
WORKDIR /workspace

# Default to bash
CMD ["bash"]