#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Docker installation for WSL Ubuntu..."

# Step 1: Set up the Docker repository dependencies
echo "Updating package index and installing dependencies..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# Step 2: Add Docker's official GPG key
echo "Adding Docker's official GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Step 3: Add the repository to your Apt sources
echo "Adding Docker repository to Apt sources..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Step 4: Install Docker Engine
echo "Installing Docker Engine and related plugins..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Step 5: Allow running Docker without sudo
echo "Adding the current user ($USER) to the docker group..."
sudo usermod -aG docker $USER

# Step 6: Start the Docker Daemon
echo "Starting the Docker service..."
if pidof systemd &> /dev/null; then
    # Systemd is running (newer WSL2 default)
    echo "Detected systemd. Enabling and starting Docker via systemctl..."
    sudo systemctl enable docker
    sudo systemctl start docker
else
    # Systemd is not running (older WSL setups)
    echo "Systemd not detected. Starting Docker via service..."
    sudo service docker start
fi

echo "======================================================================="
echo "Docker installation is complete!"
echo ""
echo "IMPORTANT: To apply the group changes (so you can run Docker without 'sudo'),"
echo "you must completely close this terminal window and open a new one."
echo ""
echo "Once you open a new terminal, verify the installation by running:"
echo "  docker run hello-world"
echo "======================================================================="