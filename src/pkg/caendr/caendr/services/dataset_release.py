from logzero import logger

from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity, delete_ds_entity_by_ref
from caendr.models.datastore import DatasetRelease
from caendr.models.sql import Strain
from caendr.models.error import UnprocessableEntity, BadRequestError


def get_release_bucket():
  return DatasetRelease.get_bucket_name()


def get_release_path(release_version: str=None):
  if not release_version:
    release_version = get_latest_dataset_release_version()
  
  blob_prefix = DatasetRelease.get_blob_prefix()
  return f'{blob_prefix}/{release_version}'


def get_browser_tracks_path(release_version=None):
  release_path = get_release_path()
  return f'{release_path}/browser_tracks'


def get_all_dataset_releases(keys_only=False, order=None, placeholder=True):
  ''' Returns a list of all Dataset Release entities in datastore as DatasetRelease objects '''
  logger.debug(f'get_all_dataset_releases(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(DatasetRelease.kind, keys_only=keys_only, order=order)
  if len(list(ds_entities)) == 0:
    if placeholder:
      return [_get_placeholder_dataset_release()]
  
  logger.debug(ds_entities)
  return [DatasetRelease(e.key.name) for e in ds_entities]


def _get_placeholder_dataset_release():
  ''' Returns an empty release as a placeholder to use when none exist '''
  release = DatasetRelease()
  release.set_properties(version='None', report_type='V0', disabled=True, hidden=False)
  return release


def get_dataset_release(version: str):
  ''' Returns a DatasetRelease object for a release version if it exists '''
  release = DatasetRelease(version)
  if not release:
    raise UnprocessableEntity('Dataset release: version:{version} does not exist.')
  return release


def get_latest_dataset_release_version():
  releases = get_all_dataset_releases(order='-version', keys_only=True)
  if len(releases) > 0:
    latest_release = releases[0]
    return latest_release


def create_new_dataset_release(version: str, wormbase_version: str, report_type: str, disabled: bool=False, hidden: bool=False):
  logger.debug(f'Creating new DatasetRelease: version:{version} wormbase_version:{wormbase_version} report_type:{report_type} disabled:{disabled} hidden:{hidden}')
  
  ds_entity = get_ds_entity(DatasetRelease.kind, version)
  if ds_entity:
    raise BadRequestError(f'Dataset release: version:{version} already exists!')
  
  release = DatasetRelease(version)
  PROPS = {'version': version, 
          'wormbase_version': wormbase_version,
          'report_type': report_type,
          'disabled': disabled,
          'hidden': hidden}
  release.set_properties(**PROPS)
  release.save()
  return release


def update_dataset_release(id: str, **kwargs):
  logger.debug(f'Updating existing DatasetRelease: **kwargs:{kwargs}')
  d = get_dataset_release(id)
  d.set_properties(**kwargs)
  d.save()
  return d


def delete_dataset_release(version: str):
  delete_ds_entity_by_ref(DatasetRelease.kind, version)


def get_release_summary(release: str):
  """
      Returns isotype and strain count for a data release.
      Args:
          release - the data release
  """
  release = int(release)
  strain_count = Strain.query.filter((Strain.release <= release) & (Strain.issues == False)).count()
  strain_count_sequenced = Strain.query.filter((Strain.release <= release) & (Strain.issues == False) & (Strain.sequenced == True)).count()
  isotype_count = Strain.query.with_entities(Strain.isotype).filter((Strain.isotype != None), (Strain.release <= release), (Strain.issues == False)).group_by(Strain.isotype).count()
  
  return {
    'strain_count': strain_count,
    'strain_count_sequenced': strain_count_sequenced,
    'isotype_count': isotype_count
  }