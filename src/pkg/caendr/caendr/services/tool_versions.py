import os
from caendr.services.logger import logger
import urllib.parse

from caendr.services.cloud.docker_hub import get_container_versions
from caendr.services.cloud import gcr_container_registry
from caendr.services.cloud.datastore import query_ds_entities
from caendr.models.datastore import Container


NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')
INDEL_PRIMER_CONTAINER_NAME = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')
HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')

MODULE_DB_OPERATIONS_CONTAINER_NAME = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_VERSION')
DOCKER_HUB_REPO_NAME = os.environ.get('DOCKER_HUB_REPO_NAME')
GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')

GCR_REPO_NAME = f'gcr.io/{GOOGLE_CLOUD_PROJECT_ID}'

def get_available_version_tags(container):
  versions = []
  if hasattr(container, 'container_repo') and container.container_repo.startswith('gcr.io/'):
    versions = get_available_version_tags_gcr(container)
  versions = get_available_version_tags_dockerhub(container)

  return versions


def get_available_version_tags_gcr(container):
  return  gcr_container_registry.get_container_versions(container.name)


def get_available_version_tags_dockerhub(container):
  versions = get_container_versions(f'{container.container_repo}/{container.container_name}')
  versions = [ version['name'] for version in versions ]
  return versions


def get_container(id: str):
  return Container(id)


def get_version(c: Container):
  return c.container_tag


def update_version(c: Container, ver: str):
  c.container_tag = ver
  c.save()
  return c


def create_default_container_version(container_name: str, repo=DOCKER_HUB_REPO_NAME, tag=None):
  t = Container(container_name)
  if not tag:
    tag = get_available_version_tags(container_name)[-1]
  t.set_properties(repo=repo, container_name=container_name, container_tag=tag)
  return t


def get_all_containers():
  nemascan_nxf = Container(NEMASCAN_NXF_CONTAINER_NAME)
  if not nemascan_nxf._exists:
    nemascan_nxf = create_default_container_version(NEMASCAN_NXF_CONTAINER_NAME)
    nemascan_nxf.save()
    
  indel_primer = Container(INDEL_PRIMER_CONTAINER_NAME)
  if not indel_primer._exists:
    indel_primer = create_default_container_version(INDEL_PRIMER_CONTAINER_NAME)
    indel_primer.save()
    
  heritability = Container(HERITABILITY_CONTAINER_NAME)
  if not heritability._exists:
    heritability = create_default_container_version(HERITABILITY_CONTAINER_NAME)
    heritability.save()

  db_operations = Container(MODULE_DB_OPERATIONS_CONTAINER_NAME)
  if not db_operations._exists:
    db_operations = create_default_container_version(MODULE_DB_OPERATIONS_CONTAINER_NAME, repo=GCR_REPO_NAME, tag=MODULE_DB_OPERATIONS_CONTAINER_VERSION)

  return [nemascan_nxf, indel_primer, heritability, db_operations]


def get_current_container_version(container_name: str):
  return Container.get(container_name)