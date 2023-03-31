import os
from caendr.services.logger import logger

from caendr.models.datastore import GeneBrowserTracks
from caendr.models.task import GeneBrowserTracksTask, TaskStatus
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.utils.data import unique_id


MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME')
MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION')



# TODO: Does keys_only make sense as a parameter? Seems like it was originally used to limit the ds query
#       to keys, which would then be mapped to DatasetRelease objects, but since Entity.query_ds handles
#       that mapping, passing keys_only in creates DatasetRelease objects missing almost all of their fields.
def get_all_gene_browser_tracks(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_gene_browser_tracks(keys_only={keys_only}, order={order})')
  return GeneBrowserTracks.query_ds(keys_only=keys_only, order=order)


def create_new_gene_browser_track(wormbase_version, username, note=None):
  logger.debug(f'Creating new Gene Browser Tracks: wormbase_version:{wormbase_version}, username:{username}, note:{note}')

  # Compute unique ID for new Gene Browser Tracks entity
  id = unique_id()

  # Create Gene Browser Tracks entity & upload to datastore
  t = GeneBrowserTracks(id, **{
    'id':                id,
    'note':              note,
    'wormbase_version':  wormbase_version,
    'username':          username,
    'container_repo':    GCR_REPO_NAME,
    'container_name':    MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME,
    'container_version': MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION,
  })
  t.save()

  # Schedule mapping in task queue
  task   = GeneBrowserTracksTask(t)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  t.status = TaskStatus.SUBMITTED if result else TaskStatus.ERROR
  t.save()

  # Return resulting Gene Browser Tracks entity
  return t


def update_gene_browser_track_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_gene_browser_track_status: id:{id} status:{status} operation_name:{operation_name}')
  t = GeneBrowserTracks(id)
  if status:
    t.set_properties(status=status)
  if operation_name:
    t.set_properties(operation_name=operation_name)
    
  t.save()
  return t
  
