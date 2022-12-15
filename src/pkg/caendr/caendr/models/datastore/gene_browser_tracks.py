import json
import os

from pathlib import Path

from caendr.models.datastore import Entity



MODULE_GENE_BROWSER_TRACKS_PATH = os.environ.get('MODULE_GENE_BROWSER_TRACKS_PATH')
MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


class GeneBrowserTracks(Entity):
  kind = 'gene_browser_tracks'
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = MODULE_GENE_BROWSER_TRACKS_PATH

  def __init__(self, *args, **kwargs):
    super(GeneBrowserTracks, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_props_set(cls):
    return {'id',
            'note', 
            'username',
            'wormbase_version',
            'container_name',
            'container_version',
            'container_repo',
            'operation_name',
            'status'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"



def get_tracks():

  # Get path to current file
  path = Path(os.path.dirname(__file__))

  # Load the JSON file with the browser tracks
  # with open(f"{str(path.parents[5])}/{os.environ['MODULE_GENE_BROWSER_TRACKS_JSON_PATH']}") as f:
  with open(f"{str(path.parents[5])}/data/browser_tracks.json") as f:
    tracks = json.load(f)

  # Filter out any hidden tracks
  tracks['tracks'] = {
    key: val
      for key, val in tracks['tracks'].items()
      if not val.get('hidden', False)
  }

  return tracks['tracks'], tracks['paths'], tracks['templates']

# Expose track info from JSON
TRACKS, TRACK_PATHS, TRACK_TEMPLATES = get_tracks()
