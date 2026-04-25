# An exploration setting up a containerised claude setup

## Working in WSL you will need to install docker

./install-docker.sh

## Build the docker image from the Dockerfile

docker build -t claude-sandbox-image .

## Make the networks and run the services

Run docker compose up
