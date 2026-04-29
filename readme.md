# An exploration setting up a containerised claude setup

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

## Make the networks and run the services

docker compose up

## Enter the container
docker exec -u devuser -it claude-setup-claude-sandbox-1 bash

rm -rf /homeless-shelter
rm -rf /workspace/active_repo/backend/.devenv
rm -rf /workspace/active_repo/backend/.direnv
export XDG_RUNTIME_DIR=/tmp