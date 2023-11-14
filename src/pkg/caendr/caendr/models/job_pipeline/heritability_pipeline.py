import csv

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import HeritabilityReport
from caendr.models.task            import HeritabilityTask
from caendr.models.run             import HeritabilityRunner

# Services
from caendr.models.datastore       import Species
from caendr.models.error           import DataFormatError
from caendr.services.validate      import get_delimiter_from_filepath, validate_file, NumberValidator, StrainValidator, TraitValidator
from caendr.services.cloud.storage import upload_blob_from_file
from caendr.utils.env              import get_env_var
from caendr.utils.file             import get_file_hash


HERITABILITY_CONTAINER_NAME = get_env_var('HERITABILITY_CONTAINER_NAME')



class HeritabilityPipeline(JobPipeline):

  _Report_Class = HeritabilityReport
  _Task_Class   = HeritabilityTask
  _Runner_Class = HeritabilityRunner

  _Container_Name = HERITABILITY_CONTAINER_NAME


  #
  # Parsing
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

    # Extract local filepath from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_path = data['filepath']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Get the file format & delimiter
    delimiter = get_delimiter_from_filepath(local_path, valid_file_extensions=valid_file_extensions)

    # Validate each line in the file
    # Will raise an error if any problems are found, otherwise silently passes
    validate_file(local_path, cls.column_validators(data), delimiter=delimiter, unique_rows=True)

    # Extra validation - check that five or more unique strains are provided
    unique_strains = set()

    # Open the file, skipping the header line
    with open(local_path, 'r') as f:
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
    data_hash = get_file_hash(local_path, length=32)

    # Extract trait from table data
    data['trait'] = csv_row[2]

    return {
      'props': data,
      'hash':  data_hash,
      'files': [local_path],
    }


  #
  # File Storage
  #

  def upload(self, data_files):

    # Heritability only takes one upload file
    if len(data_files) > 1:
      raise ValueError('Only one data file should be uploaded.')

    # If no files provided, skip
    if len(data_files) == 0: return

    bucket = self.report.get_bucket_name()
    blob   = self.report.get_data_blob_path()
    upload_blob_from_file(bucket, data_files[0], blob)
