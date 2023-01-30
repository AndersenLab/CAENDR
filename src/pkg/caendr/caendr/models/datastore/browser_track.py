from caendr.models.datastore import Entity


SITE_PREFIX = "//storage.googleapis.com"


class BrowserTrack(Entity):

  __release_path = "caendr-site-public-bucket/dataset_release/c_${SPECIES}/${RELEASE}"
  __bam_bai_path = "caendr-site-private-bucket/bam"


  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is BrowserTrack:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(BrowserTrack, cls).__new__(cls)


  ## Filepaths ##

  @classmethod
  def release_path(cls):
    return cls.__release_path

  @classmethod
  def bam_bai_path(cls):
    return cls.__bam_bai_path

  def get_path(self):
    '''
      Get the path in GCP to this specific Browser Track. Overwritten in subclass(es).
    '''
    return BrowserTrack.__release_path

  def get_url_template(self):
    return f'{ SITE_PREFIX }/{ self.get_path() }/{ self["filename"] }'


  ## FASTA ##

  @classmethod
  def get_fasta_filename(cls):
    return "browser_tracks/c_${SPECIES}.${PRJ}.${WB}.genome.fa"

  @classmethod
  def get_fasta_path_full(cls):
    return f'{ SITE_PREFIX }/{ cls.release_path() }/{ cls.get_fasta_filename() }'


  ## Props ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'filename',
      'name',
      'order',
      'hidden',
      'params',
    }


  @property
  def params(self):
    '''
      The params object includes some fields stored elsewhere in the Entity. These are included in
      params when getting and filtered out when setting, to maintain one source of truth.
    '''

    # Include name, order, URL in params dict
    params = {
      **self.__dict__.get('params', {}),
      'name':  self['name'],
      'order': self['order'],
      'url':   self.get_url_template(),
    }

    # Add indexURL if defined
    if self.__class__ == BrowserTrackTemplate and self['index_suffix']:
      params['indexURL'] = params['url'] + self['index_suffix']

    return params


  @params.setter
  def params(self, val):
    # Filter out params that draw from object props
    self.__dict__['params'] = {
      k: v for k, v in val.items() if k not in ['name', 'order', 'url', 'indexURL']
    }


  ## Querying ##

  @classmethod
  def query_ds_visible(cls, *args, **kwargs):
    '''
      Query only Browser Tracks that are not hidden.
      Equivalent to adding filter 'hidden = False' to the regular Entity.query_ds() method.
    '''
    kwargs['filters'] = [ *kwargs.get('filters', {}), ('hidden', '=', False) ]
    return cls.query_ds(*args, **kwargs)


  



class BrowserTrackDefault(BrowserTrack):
  kind = 'browser_track_default'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'checked',
      'source',
    }



class BrowserTrackTemplate(BrowserTrack):
  kind = 'browser_track_template'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'template_name',
      'index_suffix',
      'is_bam',
    }

  def get_path(self):
    if self['is_bam']:
      return BrowserTrack.bam_bai_path()
    else:
      return super().get_path()

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'template_name', 'no-name')}>"
