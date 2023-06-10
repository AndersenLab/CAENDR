#!/bin/bash

IMAGE_URI=northwesternmti/heritability-gls-base:latest

echo "Running image: $IMAGE_URI"
docker run -it $IMAGE_URI /bin/bash

