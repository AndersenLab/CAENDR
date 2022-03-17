import os
import subprocess
import json

from logzero import logger

from caendr.utils.data import AltTemplate

GCR_REPO_NAME = os.environ.get('GCR_REPO_NAME')

VALID_REPOS = [
  "caendr-db-operations"
]

def get_container_versions(container_name: str):
  if not container_name in VALID_REPOS:
    logger.warn(f"Invalid container name: {container_name}")    
    return []

  cmd = f"gcloud container images list-tags gcr.io/{GCR_REPO_NAME}/{container_name} --format=json"
  result, versions_json = subprocess.getstatusoutput(cmd)
  assert(result == 0)
  versions = json.loads(versions_json)
  tags = [ row['tags'][0] for row in versions if len(row['tags']) > 0 ]
  return tags