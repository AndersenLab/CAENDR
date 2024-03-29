import csv

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import HeritabilityReport
from caendr.models.run             import GCPCloudRunRunner
from caendr.models.task            import HeritabilityTask

# Services
from caendr.models.datastore       import Species
from caendr.models.error           import DataFormatError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.status          import JobStatus
from caendr.services.validate      import validate_file, NumberValidator, StrainValidator, TraitValidator
from caendr.utils.data             import get_delimiter_from_filepath
from caendr.utils.env              import get_env_var
from caendr.utils.file             import get_file_hash
from caendr.utils.local_files      import LocalUploadFile

from caendr.services.cloud.storage import download_blob_as_dataframe, BlobURISchema


HERITABILITY_CONTAINER_NAME = get_env_var('HERITABILITY_CONTAINER_NAME')



class HeritabilityPipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = HeritabilityReport
  _Task_Class   = HeritabilityTask
  _Runner_Class = GCPCloudRunRunner

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class
  runner: _Runner_Class

  _Container_Name = HERITABILITY_CONTAINER_NAME


  #
  # Parsing Submission
  #

  @classmethod
  def column_validators(cls, data):
    '''
      Create a ColumnValidator object for each column in the file
    '''
    return [
      NumberValidator( 'AssayNumber' ),
      StrainValidator( 'Strain', species=Species.from_name(data['species']) ),
      TraitValidator(  'TraitName' ),
      NumberValidator( 'Replicate' ),
      NumberValidator( 'Value', accept_float=True ),
    ]


  @classmethod
  def parse(cls, data, valid_file_extensions=None):

    # Extract local file from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_file: LocalUploadFile = data['file']
    data = { k: v for k, v in data.items() if k != 'file' }

    # Get the file format & delimiter
    delimiter = get_delimiter_from_filepath(local_file.local_path, valid_file_extensions=valid_file_extensions)

    # Validate each line in the file
    # Will raise an error if any problems are found, otherwise silently passes
    validate_file(local_file, cls.column_validators(data), delimiter=delimiter, unique_rows=True)

    # Extra validation - check that five or more unique strains are provided
    unique_strains = set()

    # Open the file, skipping the header line
    with open(local_file, 'r') as f:
      csv_reader = csv.reader(f, delimiter=delimiter)
      next(csv_reader)

      # Track all unique strain vals in a set
      for line in csv_reader:
        unique_strains.add(line[1])
        csv_row = line

    # Raise an error if not enough strains were found
    if len(unique_strains) < 5:
      raise DataFormatError("The heritability data contain fewer than five unique strains. Please be sure to measure trait values for at least five wild strains in at least three independent assays.")

    # Compute hash from file
    data_hash = get_file_hash(local_file, length=32)

    # Extract trait from table data
    data['trait'] = csv_row[2]

    return {
      'props': data,
      'hash':  data_hash,
      'files': [local_file],
    }



  #
  # Fetching & Parsing Input
  #

  def _parse_input(self, blob):

    # Download data
    data = download_blob_as_dataframe(blob)

    # If data file is empty, raise an error
    if data is None or data.empty:
      raise EmptyReportDataError(self.report.id)

    # Parse data file
    data['AssayNumber'] = data['AssayNumber'].astype(int)
    data['label'] = data.apply(lambda x: f"{x['AssayNumber']}: {x['Value']}", 1)

    # Return parsed data
    return data.to_dict('records')



  #
  # Fetching & Parsing Output
  #


  def fetch_output(self, raw: bool = False):
    result = super().fetch_output(raw=raw)

    # If result exists and report status hasn't been marked as finished yet, update it
    if result is not None and not self.is_finished():
      self.report.set_status( JobStatus.COMPLETE )
      self.report.save()

    # Return the result
    return result


  def _parse_output(self, blob):

    # Download results
    result = download_blob_as_dataframe(blob)

    # If file exists but there are no results, raise an error
    if result is None or result.empty:
      raise EmptyReportResultsError(self.report.id)

    # Convert to dict, using the 'type' column as the key instead of the index
    # Should create dictionary with two keys: 'broad-sense' and 'narrow-sense'
    return {
      i['type']: { key: val for key, val in i.items() if key != 'type' }
      for i in result.to_dict('records')
    }



  #
  # Run Configuration
  #

  def construct_command(self):
    if self.container_version == "v0.1a":
      return ['python', '/h2/main.py']
    return ["./heritability-nxf.sh"]

  def construct_environment(self):
    data_bucket, data_blob = self.report.data_directory(schema=BlobURISchema.PATH)
    return {

      # Gather any vars from the parent class(es)
      **super().construct_environment(),

      # Gather standard data paths for a report
      **self.report.get_data_paths(schema=BlobURISchema.GS),

      # Define vars for this job
      'SPECIES':        self.report['species'],
      'VCF_VERSION':    Species.get(self.report['species'])['release_latest'],
      'DATA_HASH':      self.report.data_hash,

      'DATA_BUCKET':    data_bucket,
      'DATA_BLOB_PATH': data_blob,
    }

  def construct_run_params(self):
    return {
      **super().construct_run_params(),
      'BOOT_DISK_SIZE_GB': 10,
      'TIMEOUT':           '9000s',
    }
