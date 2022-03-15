import os
from logzero import logger

from caendr.services.cloud.docker_hub import get_container_versions
from caendr.services.cloud import gcr_container_registry
from caendr.services.cloud.datastore import query_ds_entities
from caendr.models.datastore import Container


NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')
INDEL_PRIMER_CONTAINER_NAME = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')
HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')

MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME')
MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION')
MODULE_DB_OPERATIONS_CONTAINER_NAME = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_VERSION')
DOCKER_HUB_REPO_NAME = os.environ.get('DOCKER_HUB_REPO_NAME')
GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')

GCR_REPO_NAME = f'gcr.io/{GOOGLE_CLOUD_PROJECT_ID}'

def get_available_version_tags(container):
  if container.container_registry == 'gcr':
    return get_available_version_tags_gcr(container)
  
  return get_available_version_tags_dockerhub(container)


def get_available_version_tags_gcr(container):
  container_name = container.name
  versions = gcr_container_registry.get_container_versions(container_name)
  return versions


def get_available_version_tags_dockerhub(container):
  container_name = container.name    
  v = get_container_versions(f'{DOCKER_HUB_REPO_NAME}/{container_name}')
  try:
    v.remove('latest')
  except ValueError:
    pass
  return v


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
  
  db_operations = create_default_container_version(MODULE_DB_OPERATIONS_CONTAINER_NAME, repo=GCR_REPO_NAME, tag=MODULE_DB_OPERATIONS_CONTAINER_VERSION)
  
  gene_browser_tracks = create_default_container_version(MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME, repo=GCR_REPO_NAME, tag=MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION)

  return [nemascan_nxf, indel_primer, heritability, db_operations, gene_browser_tracks]


def get_current_container_version(container_name: str):
  filters =[('container_name', '=', container_name)]
  e = query_ds_entities(Container.kind, filters=filters)
  if e and e[0]:
    logger.debug(e)
    return Container(e[0])