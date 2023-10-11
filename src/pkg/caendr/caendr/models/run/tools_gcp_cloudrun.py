from .runner import GCPCloudRunRunner


#
# Database Operation (GCP CloudRun Implementation)
#
class DatabaseOperationRunner(GCPCloudRunRunner):

  _MACHINE_TYPE      = 'n1-standard-4'
  _BOOT_DISK_SIZE_GB = 50
  _VOLUME_NAME       = 'db_op_work'

  @property
  def _TIMEOUT(self):
    return '600s' if self.report['db_operation'] == 'TEST_ECHO' else '86400s'

  @property
  def _MEMORY_LIMITS(self):
    if self.report['db_operation'] == 'TEST_ECHO':
      return { 'memory': '512Mi', 'cpu': '1' }
    return { 'memory': '32Gi', 'cpu': '8' }

  @property
  def job_name(self):
    return f'db-op-{ self.report["db_operation"].lower().replace("_", "-") }'

  def construct_command(self):
    return ['/db_operations/run.sh']

  def construct_environment(self):
    environment = self.report['args']
    environment['DATABASE_OPERATION'] = self.report['db_operation']
    environment['USERNAME']           = self.report.get_user_name()
    environment['EMAIL']              = self.report.get_user_email()
    environment['OPERATION_ID']       = self.report.id

    # TODO: Do we neeed the task ID? If so, how do we obtain it?
    # environment['TASK_ID']            = self.task.id

    if self.report['args'].get('SPECIES_LIST'):
      environment['SPECIES_LIST'] = ';'.join(self.report['args']['SPECIES_LIST'])
    else:
      environment['SPECIES_LIST'] = None

    return environment


#
# Indel Primer (GCP CloudRun Implementation)
#
class IndelPrimerRunner(GCPCloudRunRunner):

  _BOOT_DISK_SIZE_GB = 20
  _TIMEOUT           = '3600s'

  def construct_command(self):
    return ['python', '/indel_primer/main.py']

  def construct_environment(self):
    return {
      "RELEASE":        self.report['release'],
      "SPECIES":        self.report['species'],
      "INDEL_STRAIN_1": self.report['strain_1'],
      "INDEL_STRAIN_2": self.report['strain_2'],
      "INDEL_SITE":     self.report['site'],
      "RESULT_BUCKET":  self.report.get_bucket_name(),
      "RESULT_BLOB":    self.report.get_result_blob_path(),
    }



#
# Heritability (GCP CloudRun Implementation)
#
class HeritabilityRunner(GCPCloudRunRunner):

  _BOOT_DISK_SIZE_GB = 10
  _TIMEOUT           = '9000s'

  def construct_command(self):
    if self.container_version == "v0.1a":
      return ['python', '/h2/main.py']
    return ["./heritability-nxf.sh"]

  def construct_environment(self):
    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(),

      "SPECIES":        self.report['species'],
      "VCF_VERSION":    self.latest_release,
      "DATA_HASH":      self.report.data_hash,
      "DATA_BUCKET":    self.report.get_bucket_name(),
      "DATA_BLOB_PATH": self.report.get_blob_path(),
    }



#
# Nemascan Mapping (GCP CloudRun Implementation)
#
class NemascanRunner(GCPCloudRunRunner):

  _BOOT_DISK_SIZE_GB = 100
  _TIMEOUT           = '86400s'
  _MEMORY_LIMITS     = { 'memory': '4Gi', 'cpu': '1' }

  def construct_command(self):
    return ['nemascan-nxf.sh']

  def construct_environment(self):
    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(),

      "SPECIES":     self.report['species'],
      "VCF_VERSION": self.latest_release,
      "USERNAME":    self.report['username'],
      "EMAIL":       self.report['email'],
    }
