from itertools import product

# Parent Class & Models
from .job_pipeline           import JobPipeline
from caendr.models.datastore import DatabaseOperation
from caendr.models.run       import GCPCloudRunRunner
from caendr.models.task      import DatabaseOperationTask

# Services
from caendr.models.datastore import Species, DbOp
from caendr.models.error     import DataFormatError, PreflightCheckError
from caendr.services.sql.etl import StrainConfig, WormbaseGeneConfig, WormbaseGeneSummaryConfig, StrainAnnotatedVariantConfig
from caendr.utils.env        import get_env_var



DB_OPERATIONS_CONTAINER_NAME = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_NAME')



# Get lists of required files from TableConfig objects
REQUIRED_FILES = {
  DbOp.DROP_AND_POPULATE_STRAINS: [
    *StrainConfig.files.values(),
  ],
  DbOp.DROP_AND_POPULATE_WORMBASE_GENES: [
    *WormbaseGeneConfig.files.values(),
    *WormbaseGeneSummaryConfig.files.values(),
  ],
  DbOp.DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS: [
    *StrainAnnotatedVariantConfig.files.values()
  ],
  DbOp.DROP_AND_POPULATE_ALL_TABLES: [
    *StrainConfig.files.values(),
    *WormbaseGeneConfig.files.values(),
    *WormbaseGeneSummaryConfig.files.values(),
    *StrainAnnotatedVariantConfig.files.values()
  ],
  DbOp.TEST_ECHO: [],
  DbOp.TEST_MOCK_DATA: [],
}



class DatabaseOperationPipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = DatabaseOperation
  _Task_Class   = DatabaseOperationTask
  _Runner_Class = GCPCloudRunRunner

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class
  runner: _Runner_Class

  _Container_Name = DB_OPERATIONS_CONTAINER_NAME



  #
  # Parsing Submission
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):
    '''
      Check that all files required for a given operation & species list are defined.
      Returns a list of all missing files.  If list is empty, no files are missing.
    '''

    # Get and validate the operation
    try:
      db_operation = data['db_op']
    except:
      raise DataFormatError('Missing field "db_operation".')
    try:
      db_operation = DbOp[db_operation]
    except:
      raise DataFormatError(f'Invalid database operation name "{db_operation}"')

    # Map list of species IDs to species objects
    species_list = data.get('species')
    if species_list is None or len(species_list) == 0:
      species_list = Species.all().keys()
    species_list = [ Species.from_name(key) for key in species_list ]

    # Loop through all required files, tracking those that don't appear in the database
    missing_files = []
    for resource_watcher, species in product(REQUIRED_FILES.get(db_operation, []), species_list):
      if not resource_watcher.check_exists(species):
        missing_files.append(f'- { resource_watcher.get_print_uri(species) }')

    # If any files were missing, raise them
    if len(missing_files) > 0:
      raise PreflightCheckError(missing_files)

    # Package the data into report properties
    return {
      'props': {
        'db_operation':   db_operation,
        'note':           data.get('node'),
        'args': {
          'SPECIES_LIST': data.get('species'),
        },
      },
    }



  # Database operations are always linked to unique executions (i.e. not cached),
  # so this check should always fail to find any matches.
  # Overrides parent definition
  def _check_existing_job_execution(self):
    return


  # Try injecting the user email as a parameter to the Task init function
  @classmethod
  def create_task(cls, *args, **kwargs):
    try:
      return super().create_task(*args, email = args[0].get_user_email(), **kwargs)
    except:
      return super().create_task(*args, **kwargs)



  #
  # Parsing Input & Output
  # DB Operation does not use input or output files, but these methods are required by the template class
  #

  def _parse_input(self, blob):
    raise ValueError(f'Job pipeline for kind "{self.kind}" does not produce an input file.')

  def _parse_output(self, blob):
    raise ValueError(f'Job pipeline for kind "{self.kind}" does not produce an output file.')



  #
  # Run Configuration
  #

  def construct_command(self):
    return ['/db_operations/run.sh']


  def construct_environment(self):

    # Convert the species list to a semicolon-separated string, defaulting to None if no species provided
    species_list = ';'.join( self.report['args'].get('SPECIES_LIST', []) ) or None

    # TODO: Do we neeed the task ID? If so, how do we obtain it?
    # environment['TASK_ID']            = self.task.id

    return {
      **super().construct_environment(),
      **self.report['args'],
      'DATABASE_OPERATION': self.report.get_data_id(as_str=True),
      'USERNAME':           self.report.get_user_name(),
      'EMAIL':              self.report.get_user_email(),
      'OPERATION_ID':       self.report.id,
      'SPECIES_LIST':       species_list,
    }


  def construct_run_params(self):

    # Use a smaller machine for test echo
    if self.report.get_data_id() == DbOp.TEST_ECHO:
      op_specific_params = {
        'TIMEOUT':         '600s',
        'MEMORY_LIMITS':   { 'memory': '512Mi', 'cpu': '1' },
      }
    else:
      op_specific_params = {
        'TIMEOUT':         '86400s',
        'MEMORY_LIMITS':   { 'memory': '32Gi', 'cpu': '8' },
      }

    # Compose params into a single dict
    return {
      **super().construct_run_params(),
      **op_specific_params,
      'MACHINE_TYPE':      'n1-standard-4',
      'BOOT_DISK_SIZE_GB': 50,
      'VOLUME_NAME':       'db_op_work',
    }
