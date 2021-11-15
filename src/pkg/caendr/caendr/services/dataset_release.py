from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity
from caendr.models.datastore import DatasetRelease


def get_all_releases(keys_only=False, order=None):
  ''' Returns a list of all Dataset Release entities in datastore as DatasetRelease objects '''
  ds_entities = query_ds_entities(DatasetRelease.kind, keys_only=keys_only)
  return [DatasetRelease(e) for e in ds_entities]


def get_placeholder_release():
  ''' Returns an empty release as a placeholder to use when none exist '''
  return DatasetRelease(version='None', report_type='V0', disabled=True)


def get_release_version(version):
  ''' Returns a DatasetRelease object for a release version if it exists, otherwise returns None '''
  ds_entity = get_ds_entity(DatasetRelease.kind, str(version))
  if not ds_entity or not ds_entity._exists:
    return None
  return DatasetRelease(ds_entity)

