# An exploration setting up a containerised claude setup

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

OR 

docker build -f Dockerfile.alpha -t my-alpha-image .

## Make the networks and run the services

docker compose up -d

### Optionally set the target repo and ports
TARGET_REPO_ABS=/path/to/repo1 \
API_PORT=8082 \
ADMIN_PORT=9001 \
UI_PORT=8081 \
SANDBOX_IMAGE=my-alpha-image \
docker compose -p project-alpha up -d

## Enter the container
docker exec -u devuser -it claude-setup-claude-sandbox-1 bash

### Optionally enter the named version
docker exec -u devuser -it project-alpha-claude-sandbox-1 bash

# 1. Install prerequisites
sudo apt update && sudo apt install -y curl ca-certificates gnupg

# 2. Add gVisor's official signing key
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg

# 3. Add the repository to your APT sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list

# 4. Install runsc
sudo apt update && sudo apt install -y runsc