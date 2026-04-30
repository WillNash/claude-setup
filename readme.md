# An exploration setting up a containerised claude setup

The aim is to have an isolated setup that stops claude or other agents from accessing files outside the mounted volume
The volume is mounted into a read only folder and copied into an active folder so cluade can make edits

This was build for a specific project, and runs devenv inside to set up a database and install needed packages
to run a server. These are not needed in a general case.

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

## Make the networks and run the services
I use port 8081 to avoid conflicts on 8080

HOST_PORT=8081 docker compose up -d



## Enter the container
docker exec -u devuser -it claude-setup-claude-sandbox-1 bash

the container has no git permissions currently, so fetch on the host
and then locally
git fetch /workspace/readonly_repo