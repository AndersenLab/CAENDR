import os
from logzero import logger

from caendr.models.datastore import GeneBrowserTracks
from caendr.models.task import GeneBrowserTracksTask
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.task import add_task
from caendr.services.cloud.secret import get_secret
from caendr.utils.data import unique_id


MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME')
MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION = os.environ.get('MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION')
MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME = os.environ.get('MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME')

MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)


def get_all_gene_browser_tracks(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_gene_browser_tracks(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(GeneBrowserTracks.kind, keys_only=keys_only, order=order)
  logger.debug(ds_entities)
  return [GeneBrowserTracks(e.key.name) for e in ds_entities]

  
  
def create_new_gene_browser_track(wormbase_version, username, note=None):
  logger.debug(f'Creating new Gene Browser Tracks: wormbase_version:{wormbase_version}, username:{username}, note:{note}')
  
  id = unique_id()
  props = {'id': id,
          'note': note, 
          'wormbase_version': wormbase_version,
          'username': username,
          'container_repo': GCR_REPO_NAME,
          'container_name': MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME,
          'container_version': MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION}
  t = GeneBrowserTracks(id)
  t.set_properties(**props)
  t.save()
  
  # Schedule mapping in task queue
  task = _create_gene_browser_track_task(t)
  payload = task.get_payload()
  task = add_task(MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME, F'{API_PIPELINE_TASK_URL}/task/start/{MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME}', payload)
  t = GeneBrowserTracks(id)
  if task:
    t.set_properties(status='SUBMITTED')
  else:
    t.set_properties(status='ERROR')
  t.save()
  return t
  
  
def _create_gene_browser_track_task(t):
  return GeneBrowserTracksTask(**{'id': t.id,
                                  'kind': GeneBrowserTracks.kind,
                                  'wormbase_version': t.wormbase_version,
                                  'container_name': t.container_name,
                                  'container_version': t.container_version,
                                  'container_repo': t.container_repo})
  
  

def update_gene_browser_track_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_gene_browser_track_status: id:{id} status:{status} operation_name:{operation_name}')
  t = GeneBrowserTracks(id)
  if status:
    t.set_properties(status=status)
  if operation_name:
    t.set_properties(operation_name=operation_name)
    
  t.save()
  return t
  
