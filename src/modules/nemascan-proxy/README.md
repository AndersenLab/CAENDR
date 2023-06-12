# NemaScan Proxy

Pulls the NemaScan project from GitHub, builds the `nemascan-nxf` container, and pushes to the appropriate GCR image repository.

Usage: `./publish_container.sh` (see below for arguments).

## Command-Line Arguments

- `-t`: The `tag` to build the container with. Required.
- `-r`: Whether to `reload` the Git project.  Can omit for speed of development if building multiple versions in succession, but it's safer to reload the project to get the latest changes.

## Environment Variables

The variables `$ENV` and `$GOOGLE_APPLICATION_CREDENTIALS` must be defined before running this script.  These define the GCP environment to push the image to.