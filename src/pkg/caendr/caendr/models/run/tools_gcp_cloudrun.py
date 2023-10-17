from .runner import GCPCloudRunRunner

from caendr.models.datastore import Species


#
# Database Operation (GCP CloudRun Implementation)
#
class DatabaseOperationRunner(GCPCloudRunRunner):

  # All computations of the same operation are grouped as the same "job"
  _data_id_field = 'db_operation'


  # Properties #

  _MACHINE_TYPE      = 'n1-standard-4'
  _BOOT_DISK_SIZE_GB = 50
  _VOLUME_NAME       = 'db_op_work'

  @property
  def _TIMEOUT(self):
    return '600s' if self.data_id == 'TEST_ECHO' else '86400s'

  @property
  def _MEMORY_LIMITS(self):
    if self.data_id == 'TEST_ECHO':
      return { 'memory': '512Mi', 'cpu': '1' }
    return { 'memory': '32Gi', 'cpu': '8' }


  # Commands #

  def construct_command(self, report):
    return ['/db_operations/run.sh']

  def construct_environment(self, report):
    environment = report['args']
    environment['DATABASE_OPERATION'] = self.data_id
    environment['USERNAME']           = report.get_user_name()
    environment['EMAIL']              = report.get_user_email()
    environment['OPERATION_ID']       = report.id

    # TODO: Do we neeed the task ID? If so, how do we obtain it?
    # environment['TASK_ID']            = self.task.id

    if report['args'].get('SPECIES_LIST'):
      environment['SPECIES_LIST'] = ';'.join(report['args']['SPECIES_LIST'])
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

  def construct_environment(self, report):
    return {
      "RELEASE":        report['release'],
      "SPECIES":        report['species'],
      "INDEL_STRAIN_1": report['strain_1'],
      "INDEL_STRAIN_2": report['strain_2'],
      "INDEL_SITE":     report['site'],
      "RESULT_BUCKET":  report.get_bucket_name(),
      "RESULT_BLOB":    report.get_result_blob_path(),
    }



#
# Heritability (GCP CloudRun Implementation)
#
class HeritabilityRunner(GCPCloudRunRunner):

  _BOOT_DISK_SIZE_GB = 10
  _TIMEOUT           = '9000s'

  def construct_command(self, report):
    if report['container_version'] == "v0.1a":
      return ['python', '/h2/main.py']
    return ["./heritability-nxf.sh"]

  def construct_environment(self, report):
    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(report),

      "SPECIES":        report['species'],
      "VCF_VERSION":    Species.get(report.species)['release_latest'],
      "DATA_HASH":      report.data_hash,
      "DATA_BUCKET":    report.get_bucket_name(),
      "DATA_BLOB_PATH": report.get_blob_path(),
    }



#
# Nemascan Mapping (GCP CloudRun Implementation)
#
class NemascanRunner(GCPCloudRunRunner):

  _BOOT_DISK_SIZE_GB = 100
  _TIMEOUT           = '86400s'
  _MEMORY_LIMITS     = { 'memory': '4Gi', 'cpu': '1' }

  def construct_command(self, report):
    return ['nemascan-nxf.sh']

  def construct_environment(self, report):
    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(),

      "SPECIES":     report['species'],
      "VCF_VERSION": Species.get(report.species)['release_latest'],
      "USERNAME":    report['username'],
      "EMAIL":       report['email'],
    }
