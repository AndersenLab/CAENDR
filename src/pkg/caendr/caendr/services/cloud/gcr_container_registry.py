import os
import subprocess
import json
from shutil import which

from logzero import logger

from caendr.utils.data import AltTemplate

GCR_REPO_NAME = os.environ.get('GCR_REPO_NAME')

VALID_REPOS = [
  "caendr-db-operations"
]

def get_gcloud():
  gcloud_bin_path = os.getenv('MODULE_GCLOUD_BIN_PATH')
  if gcloud_bin_path is None:
    logger.warn("gcloud path is not set")

  logger.info("trying to find gcloud in the system path")
  gcloud_bin_path = which("gcloud")    
  if gcloud_bin_path is not None:
    logger.info(f"Found gcloud binary at [{gcloud_bin_path}]")    
    return gcloud_bin_path

  logger.warn("No gcloud found in system path")    
  return None


def get_container_versions(container_name: str):
  if not container_name in VALID_REPOS:
    logger.warn(f"Invalid container name: {container_name}")    
    return []
        
  ## download gcloud for linux
  gcloud_bin_path = get_gcloud()
  cmd = f"{gcloud_bin_path} container images list-tags gcr.io/{GCR_REPO_NAME}/{container_name} --format=json"
  result, versions_json = subprocess.getstatusoutput(cmd)
  assert(result == 0)
  versions = json.loads(versions_json)
  tags = [ row['tags'][0] for row in versions if len(row['tags']) > 0 ]
  return tags