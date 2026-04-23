FROM ubuntu:latest

# Install Git, Node.js, npm, and clean up
RUN apt-get update && \
    apt-get install -y \
        git \
        curl \
        wget \
        ca-certificates \
        nodejs \
        npm && \
    rm -rf /var/lib/apt/lists/*

# Tell Git to trust all directories, and set a default sandbox identity
RUN git config --global --add safe.directory '*' && \
    git config --global user.name "Claude Sandbox" && \
    git config --global user.email "claude@sandbox.local"
# Install code-server (Browser-based VS Code)
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install Claude Code via npm
RUN npm install -g @anthropic-ai/claude-code

# Set the default directory when the container starts
WORKDIR /workspace