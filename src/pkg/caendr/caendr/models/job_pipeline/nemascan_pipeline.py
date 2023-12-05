import csv

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import NemascanReport
from caendr.models.run             import GCPCloudRunRunner
from caendr.models.task            import NemascanTask

# Services
from caendr.models.datastore       import Species
from caendr.services.cloud.storage import BlobURISchema
from caendr.services.validate      import validate_file, NumberValidator, StrainValidator
from caendr.utils.data             import get_delimiter_from_filepath
from caendr.utils.env              import get_env_var
from caendr.utils.file             import get_file_hash
from caendr.utils.local_files      import LocalUploadFile



NEMASCAN_CONTAINER_NAME = get_env_var('NEMASCAN_NXF_CONTAINER_NAME')



class NemascanPipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = NemascanReport
  _Task_Class   = NemascanTask
  _Runner_Class = GCPCloudRunRunner

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class
  runner: _Runner_Class

  _Container_Name = NEMASCAN_CONTAINER_NAME


  #
  # Parsing Submission
  #

  @classmethod
  def column_validators(cls, data):
    '''
      Create a ColumnValidator object for each column in the file
    '''

    # Define a formatting function that customizes the message if duplicate strains are found
    # Do this so we can explicitly reference "trait" values for mapping only
    force_unique_msgs = {
      'single':  lambda x: f'Multiple lines contain duplicate trait values for the strain { x }. Please ensure that only one unique trait value exists per strain.',
      'default': lambda x: f'Multiple lines contain duplicate trait values for the same strain. Please ensure that only one unique trait value exists per strain.',
    }

    return [
      StrainValidator( 'strain', species=Species.from_name(data['species']), force_unique=True, force_unique_msgs=force_unique_msgs ),
      NumberValidator( None,     accept_float=True, accept_na=True ),
    ]


  @classmethod
  def parse(cls, data, valid_file_extensions=None):

    # Extract local file from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_file: LocalUploadFile = data['file']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Get the file format & delimiter
    delimiter = get_delimiter_from_filepath(local_file.local_path, valid_file_extensions=valid_file_extensions)

    # Validate each line in the file
    # Will raise an error if any problems are found, otherwise silently passes
    validate_file(local_file, cls.column_validators(data), delimiter=delimiter, unique_rows=True)

    # Compute hash from file
    data_hash = get_file_hash(local_file, length=32)

    # Open the file and extract the trait name from the header row
    with open(local_file, 'r') as f:
      csv_reader = csv.reader(f, delimiter=delimiter)
      header_row = next(csv_reader)
      data['trait'] = header_row[1]

    return {
      'props': data,
      'hash':  data_hash,
      'files': [local_file],
    }



  #
  # Parsing Input & Output
  #

  def _parse_input(self, blob):
    pass

  def _parse_output(self, blob):
    return blob.download_as_text()



  #
  # Run Configuration
  #

  def construct_command(self):
    return ['nemascan-nxf.sh']

  def construct_environment(self):
    return {
      # Gather any vars from the parent class(es)
      **super().construct_environment(),

      # Gather standard data paths for a report
      **self.report.get_data_paths(schema=BlobURISchema.GS),

      # Define vars for this job
      'SPECIES':     self.report['species'],
      'VCF_VERSION': Species.get(self.report['species'])['release_latest'],
      'USERNAME':    self.report['username'],
      'EMAIL':       self.report['email'],
    }

  def construct_run_params(self):
    return {
      **super().construct_run_params(),
      'BOOT_DISK_SIZE_GB': 100,
      'TIMEOUT':           '86400s',
      'MEMORY_LIMITS':     { 'memory': '4Gi', 'cpu': '1' },
    }
