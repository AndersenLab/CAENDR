# Heritability Proxy

The Heritability tool requires two Docker Images to run.

## 1. Heritability Starter 

This image is built from the repo: andersenlab/calc_heritability/Dockerfile 
and it is deployed to GCR: us-east4-docker.pkg.dev/$GOOGLE_PROJECT_ID/caendr-site-v2/heritability

THis image is ENVIRONMENT specific, and it should be built for DEV/QA/PROD.

Push Image to GCR Container Registry with:

```bash
export ENV=development
./build-and-push-starter.sh
```

## 2. Heritability Google Life Sciences Base

This image is built from the repo: andersenlab/calc_heritability/env/Dockerfile
and it is deployed to dockerhub: andersenlab/heritability_gls_base

This image is shared across environments (DEV/QA/PROD).

This image is refererenced internally by andersenlab/calc_heritability/nextflow.config 
under the GCP process with `container = andersenlab/heritability_gls_base:latest`

Push Image to Docker Hub
```bash
docker login  # enter your dockerhub credentails
./build-and-push-gls-base.sh
```