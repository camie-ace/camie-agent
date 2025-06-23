#!/bin/bash

kubectl create secret docker-registry dockerhub-credentials \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username="" \
  --docker-password="" \
  --docker-email=""