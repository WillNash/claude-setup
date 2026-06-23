# An exploration setting up a containerised claude setup

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

## Make the networks and run the services

docker compose up -d

### Optionally set the target repo and ports

TARGET_REPO_ABS=/path/to/repo1 \
API_PORT=8082 \
ADMIN_PORT=9001 \
UI_PORT=8081 \
docker compose -p project-alpha up -d

## Enter the container
docker exec -u devuser -it claude-setup-claude-sandbox-1 bash

### Optionally enter the named version
docker exec -u devuser -it project-alpha-claude-sandbox-1 bash

## Some notes on setting up KATA

### install zstd

sudo apt update && sudo apt install zstd

### Install only the needed kata containers - this installs kata-runtime

wget https://github.com/kata-containers/kata-containers/releases/download/3.30.0/kata-static-3.30.0-amd64.tar.zst

sudo tar -xf kata-static-3.30.0-amd64.tar.zst -C /

### Symlink them

sudo ln -s /opt/kata/bin/kata-runtime /usr/local/bin/kata-runtime
sudo ln -s /opt/kata/bin/containerd-shim-kata-v2 /usr/local/bin/containerd-shim-kata-v2

### Tell docker about kata 

modify /etc/docker/daemon.json
{
  "runtimes": {
    "kata-runtime": {
      "runtimeType": "io.containerd.kata.v2"
    }
  }
}

### restart docker

sudo systemctl restart docker

