# Heritability Proxy

The Heritability tool requires two Docker Images to run.

## 1. Heritability Starter 

This image is built from the repo: northwestern-mti/calc_heritability/Dockerfile 
and it is deployed to GCR: gcr.io/$GOOGLE_PROJECT_ID/heritability

THis image is ENVIRONMENT specific, and it should be built for DEV/QA/PROD.

Push Image to GCR Container Registry with:

```bash
export ENV=development
./build-and-push-starter.sh
```

## 2. Heritability Google Life Sciences Base

This image is built from the repo: northwestern-mti/calc_heritability/env/Dockerfile
and it is deployed to dockerhub: northwesternmti/heritability_gls_base

This image is shared across environments (DEV/QA/PROD).

This image is refererenced internally by northwestern-mti/calc_heritability/nextflow.config 
under the GCP process with `container = northwesternmti/heritability_gls_base:latest`

Push Image to Docker Hub
```bash
docker login  # enter your dockerhub credentails
./build-and-push-gls-base.sh
```