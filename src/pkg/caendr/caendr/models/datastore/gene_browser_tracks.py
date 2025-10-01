import os

from caendr.models.datastore import JobEntity


#
# TODO: This Entity type has been deprecated.
#
class GeneBrowserTracks(JobEntity):
  kind = 'gene_browser_tracks'

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
