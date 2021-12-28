import os

from caendr.models.datastore import Entity

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')
PROTOCOL_PDF_PATH_PREFIX = 'protocol/pdf'


class Protocol(Entity):
  kind = 'protocol'
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = PROTOCOL_PDF_PATH_PREFIX
  
  def __init__(self, *args, **kwargs):
    super(Protocol, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  @classmethod
  def get_props_set(cls):
    return {'id',
            'group', 
            'title', 
            'pdf_blob_path'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
