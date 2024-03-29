import os

from caendr.models.datastore import JobEntity



# MODULE_GENE_BROWSER_TRACKS_PATH = os.environ.get('MODULE_GENE_BROWSER_TRACKS_PATH')
# MODULE_SITE_BUCKET_PUBLIC_NAME  = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


#
# TODO: This Entity type has been deprecated.
#
class GeneBrowserTracks(JobEntity):
  kind = 'gene_browser_tracks'
  # __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  # __blob_prefix = MODULE_GENE_BROWSER_TRACKS_PATH

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

      # Submission
      'username',

      # Query
      'note', 
      'wormbase_version',
    }
