import os
import subprocess
import json
from shutil import which

from caendr.services.logger import logger

from caendr.utils.data import AltTemplate

GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')

GCR_REPO_NAME = f'gcr.io/{GOOGLE_CLOUD_PROJECT_ID}'

# from caendr.services.tool_versions import GCR_REPO_NAME

VALID_REPOS = [
  "caendr-db-operations",
  "caendr-gene-browser-tracks"
  "indel-primer",
  "heritability",
  "nemascan-nxf"
]

def get_gcloud():
  gcloud_bin_path = os.getenv('MODULE_GCLOUD_BIN_PATH')
  if gcloud_bin_path is not None and os.path.exists(gcloud_bin_path):
    return gcloud_bin_path    

  gcloud_bin_path = which("gcloud")    
  if gcloud_bin_path is not None and os.path.exists(gcloud_bin_path):
    return gcloud_bin_path

  logger.warn("gcloud binary not found")
  return None


def get_container_versions(container_name: str):
  if not container_name in VALID_REPOS:
    logger.warn(f"Invalid container name: {container_name}")    
    return []
        
  ## download gcloud for linux
  gcloud_bin_path = get_gcloud()
  cmd = f"{gcloud_bin_path} container images list-tags {GCR_REPO_NAME}/{container_name} --format=json"
  result, versions_json = subprocess.getstatusoutput(cmd)
  assert(result == 0)
  versions = json.loads(versions_json)
  tags = [ row['tags'][0] for row in versions if len(row['tags']) > 0 ]
  return tags