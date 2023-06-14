#!/bin/bash

# NOTE: this image is only built for local development/testing on a 
# developer's workstation. It should not be pushed to any continer registries.

IMG_URI=local/img_thumb_gen
docker buildx build --platform=linux/amd64  -f Dockerfile.local -t $IMG_URI . 