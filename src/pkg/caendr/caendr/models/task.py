from caendr.services.logger import logger

# Define the Status values
class TaskStatus:
  ERROR = "ERROR"
  RUNNING = "RUNNING"
  COMPLETE = "COMPLETE"
  PENDING ="PENDING"

class Task(object):
  
  def __init__(self, *args, **kwargs):
    self.set_properties(**kwargs)
    
  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
  
  @classmethod
  def get_props_set(cls):
    return {'id',
          'kind',
          'username',
          'container_name',
          'container_version',
          'container_repo'}
    
  # TODO: simplify this with __dict__ or something
  def get_payload(self):
    return {'id': self.id,
          'kind': self.kind,
          'username': self.username,
          'container_name': self.container_name,
          'container_version': self.container_version,
          'container_repo': self.container_repo}
  
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<task:{self.id}>"
    else:
      return f"<task:no-id>"

class EchoTask(Task):
  def get_payload(self):
    payload = super(EchoTask, self).get_payload()
    payload['data_hash'] = self.data_hash
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(EchoTask, cls).get_props_set()
    props.add('data_hash')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<echo_task:{self.id}>"
    else:
      return f"<echo_task:no-id>"

class MockDataTask(Task):
  def get_payload(self):
    payload = super(MockDataTask, self).get_payload()
    payload['data_hash'] = self.data_hash
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(MockDataTask, cls).get_props_set()
    props.add('data_hash')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<mock_data_task:{self.id}>"
    else:
      return f"<mock_data_task:no-id>"

class NemaScanTask(Task):
  def get_payload(self):
    payload = super(NemaScanTask, self).get_payload()
    payload['data_hash'] = self.data_hash
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(NemaScanTask, cls).get_props_set()
    props.add('data_hash')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<nemascan_task:{self.id}>"
    else:
      return f"<nemascan_task:no-id>"
    
    
    
class DatabaseOperationTask(Task):
  def get_payload(self):
    payload = super(DatabaseOperationTask, self).get_payload()
    payload['email'] = self.email
    payload['db_operation'] = self.db_operation
    payload['args'] = self.args
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(DatabaseOperationTask, cls).get_props_set()
    props.add('email')
    props.add('db_operation')
    props.add('args')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<db_op_task:{self.id}>"
    else:
      return f"<db_op_task:no-id>"
    
    
class IndelPrimerTask(Task):
  def get_payload(self):
    payload = super(IndelPrimerTask, self).get_payload()
    payload['data_hash'] = self.data_hash
    payload['strain_1'] = self.strain_1
    payload['strain_2'] = self.strain_2
    payload['site'] = self.site
    payload['sv_bed_filename'] = self.sv_bed_filename
    payload['sv_vcf_filename'] = self.sv_vcf_filename
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(IndelPrimerTask, cls).get_props_set()
    props.add('data_hash')
    props.add('strain_1')
    props.add('strain_2')
    props.add('site')
    props.add('sv_bed_filename')
    props.add('sv_vcf_filename')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<indel_primer_task:{self.id}>"
    else:
      return f"<indel_primer_task:no-id>"
    
    
class HeritabilityTask(Task):
  def get_payload(self):
    payload = super(HeritabilityTask, self).get_payload()
    payload['data_hash'] = self.data_hash
    return payload
  
  @classmethod
  def get_props_set(cls):
    props = super(HeritabilityTask, cls).get_props_set()
    props.add('data_hash')
    return props

  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<heritability_task:{self.id}>"
    else:
      return f"<heritability_task:no-id>"
    