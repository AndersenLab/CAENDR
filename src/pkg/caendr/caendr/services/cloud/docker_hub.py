import os
import subprocess

from caendr.services.logger import logger

from caendr.utils.data import AltTemplate

DOCKER_HUB_REPO_NAME = os.environ.get('DOCKER_HUB_REPO_NAME')


def get_container_versions(container_name: str):
  t = AltTemplate("wget -q https://registry.hub.docker.com/v1/repositories/%name/tags -O - | sed -e 's/[][]//g' -e 's/\"//g' -e 's/ //g' | tr '}' '\\n'  | awk -F: '{print $3}'")
  cmd = t.substitute({'name':container_name})
  result, versions_string = subprocess.getstatusoutput(cmd)
  assert(result == 0)
  versions = versions_string.split('\n')
  return versions