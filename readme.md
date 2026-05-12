# An exploration setting up a containerised claude setup

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

## Make the networks and run the services

docker compose up -d

## Enter the container
docker exec -u devuser -it claude-setup-claude-sandbox-1 bash

## Some notes on setting up KATA

### install zstd

sudo apt update && sudo apt install zstd

### Install only the needed kata containers - this installs kata-runtime

wget https://github.com/kata-containers/kata-containers/releases/download/3.30.0/kata-static-3.30.0-amd64.tar.zst

sudo tar -xf kata-static-3.30.0-amd64.tar.zst -C /

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