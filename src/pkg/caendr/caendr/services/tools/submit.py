import os
import csv
import json

from caendr.services.logger import logger

from caendr.models.datastore import Container, Species, IndelPrimer, HeritabilityReport, NemascanMapping
from caendr.models.error     import CachedDataError, DuplicateDataError, DataFormatError
from caendr.models.task      import TaskStatus, IndelPrimerTask, HeritabilityTask, NemaScanTask

from caendr.api.strain             import query_strains
from caendr.api.isotype            import get_distinct_isotypes
from caendr.services.cloud.storage import upload_blob_from_string, upload_blob_from_file

from caendr.utils.data import get_object_hash, get_file_format, join_commas_and
from caendr.utils.env  import get_env_var
from caendr.utils.file import get_file_hash



INDEL_PRIMER_CONTAINER_NAME = get_env_var('INDEL_PRIMER_CONTAINER_NAME')
HERITABILITY_CONTAINER_NAME = get_env_var('HERITABILITY_CONTAINER_NAME')
NEMASCAN_NXF_CONTAINER_NAME = get_env_var('NEMASCAN_NXF_CONTAINER_NAME')



def get_delimiter_from_filepath(filepath=None, valid_file_extensions=None):
  valid_file_extensions = valid_file_extensions or {'csv'}
  if filepath:
    file_format = get_file_format(filepath[-3:], valid_formats=valid_file_extensions)
    if file_format:
      return file_format['sep']



def submit_job(entity_class, user, data, container_version=None, no_cache=False, valid_file_extensions=None):
  '''
      Submit a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Entity_Class.

      Arguments:
        entity_class: The subclass of Entity associated with this job.
        user: The user submitting the job.
        data: The user's input data. Will be run through SubmissionManager.parse_data() and used to populate
              the datastore Entity.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created Entity representing this job submission.  Type will be determined by entity_class.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

  # Define mapping between Entity classes and Submission Manager classes
  entity_manager_mapping = {
    c._Entity_Class.kind: c
      for c in [
        IndelPrimerSubmissionManager,
        HeritabilitySubmissionManager,
        MappingSubmissionManager,
      ]
  }

  # If desired Entity class can't be found in mapping, raise error
  if getattr(entity_class, 'kind') not in entity_manager_mapping:
    raise ValueError(f'No submission manager defined for class "{entity_class.__name__}"')

  # Forward args to proper SubmissionManager subclass
  return entity_manager_mapping[entity_class.kind].submit(user, data, container_version=container_version, no_cache=no_cache, valid_file_extensions=valid_file_extensions)



class SubmissionManager():

  # The associated Entity and Task subclasses
  # Should be overridden in SubmissionManager subclasses
  _Entity_Class = None
  _Task_Class   = None


  @classmethod
  def create_entity(cls, *args, **kwargs):
    '''
      Create an Entity of the appropriate subclass type.
    '''
    return cls._Entity_Class(*args, **kwargs)

  @classmethod
  def create_task(cls, *args, **kwargs):
    '''
      Create a Task of the appropriate subclass type.
    '''
    return cls._Task_Class(*args, **kwargs)

  # Forward cache check to Entity class
  @classmethod
  def check_cached_submission(cls, *args, **kwargs):
    '''
      Check whether this user has submitted this job before.
    '''
    return cls._Entity_Class.check_cached_submission(*args, **kwargs)


  @classmethod
  def container_name(cls):
    '''
      Retrieve the container name to use to run this job.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "container_name" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "container_name".')

  @classmethod
  def upload_data_file(cls, entity, data_file):
    '''
      Upload the given data file at the location specified by the given Entity.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "upload_data_file" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "upload_data_file".')

  @classmethod
  def parse_data(cls, data, delimiter='\t'):
    '''
      Parse a data object representing the raw form input into a set of props for the Entity subclass.
      Should be overridden by subclasses.
    '''
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "parse_data" on {cls.__name__}. Please run with subclass instead.')
    elif issubclass(cls, SubmissionManager):
      raise NotImplementedError(f'Class "{cls.__name__}" should override the definition of "parse_data".')


  @classmethod
  def submit(cls, user, data, container_version=None, no_cache=False, valid_file_extensions=None):
    '''
      Submit a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Entity_Class.

      Arguments:
        user: The user submitting the job.
        data: The user's input data. Will be run through SubmissionManager.parse_data() and used to populate
              the datastore Entity.
        container_version:
          The version of the tool container to use. If None is provided, uses the most recent version.
          Defaults to None.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created Entity representing this job. The subclass of this Entity will depend on the subclass of
        SubmissionManager used to submit.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

    # Ensure this is being run on a subclass of SubmissionManager, not SubmissionManager itself
    if cls is SubmissionManager:
      raise TypeError(f'Cannot run method "submit" on {cls.__name__}. Please run with subclass instead.')

    logger.debug(f'Submitting new {cls._Entity_Class.__name__} for user "{user.name}".')

    # Load container version info
    container = Container.get(cls.container_name(), version = container_version)
    logger.debug(f"Creating {cls._Entity_Class.__name__} with Container {container.uri()}")
    if container_version is not None:
      logger.warn(f'Container version {container_version} was specified manually - this may not be the most recent version.')

    # Get the file format & delimiter
    delimiter = get_delimiter_from_filepath(data.get('filepath'), valid_file_extensions=valid_file_extensions)

    # Parse the input data
    data_file, data_hash, data_vals = cls.parse_data(data, delimiter=delimiter)

    # Check if user has already submitted this job, and "return" it in a duplicate data error if so
    if not no_cache:
      cached_entity = cls.check_cached_submission(data_hash, user.name, container, status=TaskStatus.NOT_ERR)
      if cached_entity:
        raise DuplicateDataError(cached_entity)

    # Create entity to represent this job and set data fields
    entity = cls.create_entity(**data_vals)
    entity.data_hash = data_hash

    # Set entity's container & user fields
    entity.set_container(container)
    entity.set_user(user)

    # Upload the new entity to datastore
    entity['status'] = TaskStatus.SUBMITTED # TODO: Is this an OK initial value? What if there's an error before the task is submitted?
    entity.save()

    # Check if there is already a cached result, and skip creating a job if so
    if not no_cache:
      cached_result = entity.check_cached_result()
      if cached_result:

        # If cache check returned a status, use it; otherwise, default to "COMPLETE"
        entity['status'] = cached_result if isinstance(cached_result, str) else TaskStatus.COMPLETE
        entity.save()

        # Save the entity and "return" in a cached data error
        raise CachedDataError(entity)

    # Upload source data file to data store
    cls.upload_data_file(entity, data_file)

    # Schedule job in task queue
    task   = cls.create_task(entity)
    result = task.submit()

    # Update entity status to reflect whether task was submitted successfully
    entity['status'] = TaskStatus.SUBMITTED if result else TaskStatus.ERROR
    entity.save()

    # Return resulting Job entity
    return entity


  @staticmethod
  def validate_file(local_path, columns, delimiter='\t', unique_rows=False):

    num_cols = len(columns)
    rows = {}

    # Read first line from tsv
    with open(local_path, 'r', encoding='utf-8-sig') as f:
      csv_reader = csv.reader(f, delimiter=delimiter)

      # Get the header line, throwing an empty file error if not found
      try:
        csv_headings  = next(csv_reader)
      except StopIteration:
        raise DataFormatError('The file is empty. Please edit the file to include your data.')

      # Check that first line has correct number of columns
      if len(csv_headings) != num_cols:
        raise DataFormatError(f'The file contains an incorrect number of columns. Please edit the file to ensure it contains { num_cols } columns.', 1)

      # Check first line for column headers
      invalid_headers = []
      for col in range(num_cols):
        target_header = columns[col].get('header')
        if target_header is None:
          continue
        # if isinstance(target_header, str):
        if csv_headings[col] != target_header:
          invalid_headers.append(col)
        # else:
        #   if not target_header['validator'](csv_headings[col]):
        #     raise DataFormatError(f'The file contains an incorrect column header. { target_header["make_err_msg"]( col + 1, csv_headings[col] ) }', 1)

      # If one header was incorrect, flag it
      if len(invalid_headers) == 1:
        col = invalid_headers[0]
        raise DataFormatError(f'The file contains an incorrect column header. Column #{ col + 1 } should be { columns[col]["header"] }.', 1)

      # If multiple headers were incorrect, flag all of them at once
      elif len(invalid_headers) > 1:
        cs = join_commas_and([ f'#{c + 1}' for c in invalid_headers ])
        hs = join_commas_and([ c["header"] for c in columns ])
        raise DataFormatError(f'The file contains incorrect headers in columns { cs }. The full set of headers should be: { hs }.', 1)

      # Loop through all remaining lines in the file
      has_data = False
      for line, csv_row in enumerate(csv_reader, start=2):

        # Check for empty lines
        if ''.join(csv_row).strip() == '':
          raise DataFormatError(f'Rows cannot be blank. Please check line #{ line } to ensure valid data have been entered.', line)

        # Check that line has the correct number of columns
        if len(csv_row) != num_cols:
          raise DataFormatError(f'File contains incorrect number of columns. Please edit the file to ensure it contains { num_cols } columns.', line)

        # If desired, check that this row is unique
        if unique_rows:
          as_string = '\t'.join(csv_row)
          prev_line = rows.get(as_string)
          if prev_line is not None:
            raise DataFormatError(f'Line #{ line } is a duplicate of line #{ prev_line }. Please ensure that each row contains unique values.')
          else:
            rows[as_string] = line

        # Check that all columns have valid data, using the "step" validator
        for column, value in zip(columns, csv_row):
          header    = column.get('header')
          validator = column['validator']
          if 'step' in validator:
            validator['step']( header, value.strip(), line )

        # Track that we parsed at least one line of data properly
        has_data = True

      # Check that the loop ran at least once (i.e. is not just headers)
      if not has_data:
        raise DataFormatError('The file is empty. Please edit the file to include your data.')

      # Run each validator's "final" function at the end, in case any of the "step" validators were accumulating values
      for c in columns:
        if 'final' in c['validator']:
          c['validator']['final']()


class IndelPrimerSubmissionManager(SubmissionManager):

  _Entity_Class = IndelPrimer
  _Task_Class   = IndelPrimerTask

  @classmethod
  def container_name(cls):
    return INDEL_PRIMER_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_string(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data, delimiter='\t'):
    data_file = json.dumps(data)
    data_hash = get_object_hash(data, length=32)

    # TODO: Pull this value from somewhere
    release = Species.from_name( data['species'] ).release_pif

    # Add release information to data object
    data.update({
      'release':         release,
      'sv_bed_filename': IndelPrimer.get_source_filename(data['species'], release) + '.bed.gz',
      'sv_vcf_filename': IndelPrimer.get_source_filename(data['species'], release) + '.vcf.gz',
    })

    return data_file, data_hash, data



class HeritabilitySubmissionManager(SubmissionManager):

  _Entity_Class = HeritabilityReport
  _Task_Class   = HeritabilityTask

  @classmethod
  def container_name(cls):
    return HERITABILITY_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_file(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data, delimiter='\t'):

    # Extract local filepath from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_path = data['filepath']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Define an expected header & a validator function for each column in the file
    columns = [
      {
        'header': 'AssayNumber',
        'validator': validate_num(),
      },
      {
        'header': 'Strain',
        'validator': validate_strain( Species.from_name(data['species']) ),
      },
      {
        'header': 'TraitName',
        'validator': validate_trait(),
      },
      {
        'header': 'Replicate',
        'validator': validate_num(),
      },
      {
        'header': 'Value',
        'validator': validate_num(accept_float=True),
      },
    ]

    # Validate each line in the file
    # Will raise an error if any problems are found, otherwise silently passes
    SubmissionManager.validate_file(local_path, columns, delimiter=delimiter, unique_rows=True)

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

    return local_path, data_hash, data



class MappingSubmissionManager(SubmissionManager):

  _Entity_Class = NemascanMapping
  _Task_Class   = NemaScanTask

  @classmethod
  def container_name(cls):
    return NEMASCAN_NXF_CONTAINER_NAME

  @classmethod
  def upload_data_file(cls, entity, data_file):
    bucket = entity.get_bucket_name()
    blob   = entity.get_data_blob_path()
    upload_blob_from_file(bucket, data_file, blob)

  @classmethod
  def parse_data(cls, data, delimiter='\t'):

    # Extract local filepath from the data object
    # Note that we don't change the underlying object itself, as this would
    # affect the data dict in calling functions
    local_path = data['filepath']
    data = { k: v for k, v in data.items() if k != 'filepath' }

    # Validate file upload
    logger.debug(f'Validating Nemascan Mapping data format: {local_path}')

    # Define a formatting function that customizes the message if duplicate strains are found
    # Do this so we can explicitly reference "trait" values for mapping only
    duplicate_strain_formatter = lambda prev_line, curr_line: \
      f'Lines #{ prev_line } and #{ curr_line } contain duplicate trait values for the same strain. Please ensure that only one unique trait value exists per strain.'

    columns = [
      {
        'header': 'strain',
        'validator': validate_strain(Species.from_name(data['species']), force_unique=True, force_unique_msg=duplicate_strain_formatter)
      },
      {
        # 'header': {
        #   'validator': lambda x: x
        # },
        'validator': validate_num(accept_float=True, accept_na=True),
      },
    ]

    # Validate file
    SubmissionManager.validate_file(local_path, columns, delimiter=delimiter, unique_rows=True)

    # Compute data hash using entire file
    data_hash = get_file_hash(local_path, length=32)

    # Open the file and extract the trait name from the header row
    with open(local_path, 'r') as f:
      csv_reader = csv.reader(f, delimiter=delimiter)
      header_row = next(csv_reader)
      data['trait'] = header_row[1]

    return local_path, data_hash, data



#
# Validator Functions
#

def validate_num(accept_float = False, accept_na = False):

  # Construct a message for the expected data type
  if accept_float:
    data_type = 'decimal'
  else:
    data_type = 'integer'

  # Define the validator function
  def func(header, value, line):
    nonlocal data_type

    # Try casting the value to the appropriate num type
    try:
      if accept_float:
        float(value)
      else:
        int(value)

    # If casting fails, raise an error (with an exception for 'NA', if applicable)
    except:
      if not (accept_na and value == 'NA'):
        raise DataFormatError(f'Column { header } is not a valid { data_type }. Please edit { header } to ensure only { data_type } values are included.', line)

  return { 'step': func }


# Check that column is a valid strain name for the desired species
def validate_strain(species, force_unique=False, force_unique_msg=None):

  # Get the list of all valid strain names for this species
  # Pull from strain names & isotype names, to allow for isotypes with no strain of the same name
  valid_names_species = {
    *query_strains(all_strain_names=True, species=species.name),
    *get_distinct_isotypes(species=species.name),
  }

  # Get the list of all valid strain names for all species
  # Used to provide more informative error messages
  valid_names_all = {
    *query_strains(all_strain_names=True),
    *get_distinct_isotypes(),
  }

  # Dict to track the first line each strain occurs on
  # Used to ensure strains are unique, if applicable
  strain_line_numbers = {}

  # Provide a default message if the same strain is found more than once
  # Only used if force_unique is True and if the calling function doesn't customize this message
  if force_unique_msg is None:
    force_unique_msg = lambda prev_line, curr_line: \
      f'Lines #{ prev_line } and #{ curr_line } contain duplicate values for the same strain. Please ensure that only one unique value exists per strain.'

  problems = {
    'blank_line':     [],
    'wrong_species':  [],
    'unknown_strain': [],
  }

  # Validator function run at the end of the file
  def func_final():
    nonlocal problems


    # Blank lines #

    num_problems = len(problems['blank_line'])
    if num_problems > 0:
      line_str = join_commas_and([ p['line'] for p in problems['blank_line'] ])
      raise DataFormatError(f'Strain values cannot be blank. Please check line(s) { line_str } to ensure valid strains have been entered.')


    # Wrong species #

    prob_strains = []
    for s in problems['wrong_species']:
      if s['value'] not in prob_strains:
        prob_strains.append(s['value'])

    num_problems = len(prob_strains)
    if num_problems == 1:
      raise DataFormatError(f'The strain { prob_strains[0] } is not a valid strain for { species.short_name } in our current dataset. Please enter a valid { species.short_name } strain.')
    elif num_problems > 1:
      prob_str = join_commas_and(prob_strains, truncate=8)
      raise DataFormatError(f'The strains { prob_str } are not valid strains for { species.short_name } in our current dataset. Please enter valid { species.short_name } strains.')


    # Unknown strains #

    prob_strains = []
    for s in problems['unknown_strain']:
      if s['value'] not in prob_strains:
        prob_strains.append(s['value'])

    num_problems = len(prob_strains)
    if num_problems == 1:
      raise DataFormatError(f'The strain { prob_strains[0] } is not a valid strain name in our current dataset. Please enter valid strain names.')
    elif num_problems > 1:
      prob_str = join_commas_and(prob_strains, truncate=8)
      raise DataFormatError(f'The strains { prob_str } are not valid strain names in our current dataset. Please enter valid strain names.')


  # Validator function run on each individual line
  # Keeps track of all errors, which are then run at the end by func_final
  def func_step(header, value, line):
    nonlocal force_unique, force_unique_msg
    nonlocal strain_line_numbers, valid_names_species, valid_names_all, problems

    # Check for blank strain
    if value == '':
      problems['blank_line'].append({'value': value, 'line': line})

    # Check if strain is valid for the desired species
    elif value not in valid_names_species:
      if value in valid_names_all:
        problems['wrong_species'].append({'value': value, 'line': line})
      else:
        problems['unknown_strain'].append({'value': value, 'line': line})

    # If desired, keep track of list of strains and throw an error if a duplicate is found
    if force_unique:
      if value in strain_line_numbers:
        raise DataFormatError(force_unique_msg(prev_line=strain_line_numbers[value], curr_line=line))
      strain_line_numbers[value] = line


  # Return both validator functions
  return {
    'step': func_step,
    'final': func_final,
  }


# Check that all values in a column have the same trait name
def validate_trait():

  # Initialize var to track the single valid trait name
  trait_name = None

  # Define the validator function
  def func(header, value, line):
    nonlocal trait_name

    # If no trait name has been encountered yet, save the first value
    if trait_name is None:
      trait_name = value

    # If the trait name has been set, ensure this line matches it
    elif value != trait_name:
      raise DataFormatError(f'The data contain multiple unique trait name values. Only one trait name may be tested per file.', line)

  return { 'step': func }
