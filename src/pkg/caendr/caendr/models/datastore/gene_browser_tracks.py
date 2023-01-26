import json
import os

from pathlib import Path

from caendr.models.datastore import JobEntity



MODULE_GENE_BROWSER_TRACKS_PATH = os.environ.get('MODULE_GENE_BROWSER_TRACKS_PATH')
MODULE_SITE_BUCKET_PUBLIC_NAME  = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


class GeneBrowserTracks(JobEntity):
  kind = 'gene_browser_tracks'
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = MODULE_GENE_BROWSER_TRACKS_PATH

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_props_set(cls):
    return {
      *super(GeneBrowserTracks, cls).get_props_set(),

      # Submission
      'id',
      'username',

      # Query
      'note', 
      'wormbase_version',
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"



# TODO: Move to new Browser Track entity, since this Entity represents jobs to create new tracks
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
