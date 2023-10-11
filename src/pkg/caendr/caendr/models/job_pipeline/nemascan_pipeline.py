import csv

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import NemascanReport
from caendr.models.task            import NemascanTask
from caendr.models.run             import NemascanRunner

# Services
from caendr.models.datastore       import Species
from caendr.services.tools.submit  import validate_file, validate_num, validate_strain
from caendr.services.cloud.storage import upload_blob_from_file
from caendr.utils.env              import get_env_var
from caendr.utils.file             import get_file_hash


NEMASCAN_CONTAINER_NAME = get_env_var('NEMASCAN_NXF_CONTAINER_NAME')



class NemascanPipeline(JobPipeline):

  _Report_Class = NemascanReport
  _Task_Class   = NemascanTask
  _Runner_Class = NemascanRunner

  _Container_Name = NEMASCAN_CONTAINER_NAME


  #
  # Parsing
  #

  @classmethod
  def validator_columns(cls, data):
    '''
      Define an expected header & a validator function for each column in the file
    '''

    # Define a formatting function that customizes the message if duplicate strains are found
    # Do this so we can explicitly reference "trait" values for mapping only
    duplicate_strain_formatter = lambda prev_line, curr_line: \
      f'Lines #{ prev_line } and #{ curr_line } contain duplicate trait values for the same strain. Please ensure that only one unique trait value exists per strain.'
  
    return [
      {
        'header': 'strain',
        'validator': validate_strain(Species.from_name(data['species']), force_unique=True, force_unique_msg=duplicate_strain_formatter)
      },
      {
        'validator': validate_num(accept_float=True, accept_na=True),
      },
    ]


  @classmethod
  def parse(cls, data, delimiter='\t'):

    # Extract local filepath from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_path = data['filepath']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Validate each line in the file
    # Will raise an error if any problems are found, otherwise silently passes
    validate_file(local_path, cls.validator_columns(data), delimiter=delimiter, unique_rows=True)

    # Compute hash from file
    data_hash = get_file_hash(local_path, length=32)

    # Open the file and extract the trait name from the header row
    with open(local_path, 'r') as f:
      csv_reader = csv.reader(f, delimiter=delimiter)
      header_row = next(csv_reader)
      data['trait'] = header_row[1]

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
