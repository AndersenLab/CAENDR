from caendr.services.logger import logger

from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity, delete_ds_entity_by_ref
from caendr.models.datastore import DatasetRelease
from caendr.models.datastore.browser_track import BrowserTrack
from caendr.models.sql import Strain
from caendr.models.error import UnprocessableEntity, BadRequestError, NotFoundError


def get_release_bucket():
  return DatasetRelease.get_bucket_name()


def get_browser_tracks_path(release_version=None):
  return BrowserTrack.release_prefix()


# TODO: Does keys_only make sense as a parameter? Seems like it was originally used to limit the ds query
#       to keys, which would then be mapped to DatasetRelease objects, but since Entity.query_ds handles
#       that mapping, passing keys_only in creates DatasetRelease objects missing almost all of their fields.
def get_all_dataset_releases(keys_only=False, order=None, placeholder=True, species=None):
  ''' Returns a list of all Dataset Release entities in datastore as DatasetRelease objects '''
  logger.debug(f'get_all_dataset_releases(keys_only={keys_only}, order={order})')

  # Query the db for all dataset releases
  releases = DatasetRelease.query_ds(keys_only=keys_only, order=order)
  logger.debug(releases)

  # If none were found and a placeholder was provided, return the placeholder
  if len(list(releases)) == 0 and placeholder:
    return [ _get_placeholder_dataset_release() ]

  if species is not None:
    releases = [ r for r in releases if r['species'].name == species]

  # Otherwise, return the retrieved releases
  return releases


def _get_placeholder_dataset_release():
  ''' Returns an empty release as a placeholder to use when none exist '''
  return DatasetRelease(version='None', report_type='V0', disabled=True, hidden=False)


def get_dataset_release(version: str):
  ''' Returns a DatasetRelease object for a release version if it exists '''
  release = DatasetRelease(version)
  if not release:
    raise UnprocessableEntity('Dataset release: version:{version} does not exist.')
  return release


def find_dataset_release(release_list, version=None):
  '''
    Choose the dataset release with a given version from a list of releases.
    If no version provided, returns the top element.
    If more than one matching version, returns the first one found.
  '''

  # If nothing provided in list, raise an error
  if not len(release_list):
    raise NotFoundError(DatasetRelease, {'version': version})

  # If no version specified, return the top element by default
  if not version:
    return release_list[0]

  # Look for the requested release
  for r in release_list:
    if r.version == version:
      return r

  # If release couldn't be found, raise an error
  raise NotFoundError(DatasetRelease, {'version': version})


def get_latest_dataset_release_version():
  releases = get_all_dataset_releases(order='-version')
  return find_dataset_release(releases)


def create_new_dataset_release(version: str, wormbase_version: str, report_type: str, disabled: bool=False, hidden: bool=False):
  logger.debug(f'Creating new DatasetRelease: version:{version} wormbase_version:{wormbase_version} report_type:{report_type} disabled:{disabled} hidden:{hidden}')
  
  ds_entity = get_ds_entity(DatasetRelease.kind, version)
  if ds_entity:
    raise BadRequestError(f'Dataset release: version:{version} already exists!')
  
  release = DatasetRelease(version, **{
    'version':          version,
    'wormbase_version': wormbase_version,
    'report_type':      report_type,
    'disabled':         disabled,
    'hidden':           hidden,
  })
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