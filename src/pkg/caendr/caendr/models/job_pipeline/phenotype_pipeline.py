from scipy import stats

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import PhenotypeReport

# Services
from caendr.models.datastore       import TraitFile
from caendr.models.error           import EmptyReportDataError, EmptyReportResultsError
from caendr.models.status          import JobStatus
from caendr.utils.data             import dataframe_cols_to_dict, get_object_hash, keyset_intersection



class PhenotypePipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = PhenotypeReport
  _Task_Class   = None
  _Runner_Class = None

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class


  # Temporary(?) override to intercept pipeline creation and mark the job as complete
  @classmethod
  def create(cls, *args, **kwargs):
    job = super().create(*args, **kwargs)
    if job.report.get_status() == JobStatus.CREATED:
      job.report.set_status(JobStatus.COMPLETE)
      job.report.save()
    return job


  #
  # Parsing Submission
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):

    # Get both trait files from the datastore, confirming they both exist
    trait_1 = TraitFile.get_ds(data['trait_1'])
    trait_2 = TraitFile.get_ds(data['trait_2'])

    # Compute hash from trait file unique IDs
    # Sort the IDs before combining, so either order will produce the same hash
    hash = get_object_hash(' '.join(sorted([trait_1.name, trait_2.name])), length=32)

    return {
      'props': data,
      'hash':  hash,
    }



  #
  # Parsing Input
  #

  def _parse_input(self, data):
    return {
      'num_traits':  len(data),
      'trait_names': tuple(map(lambda tf: tf['trait_name'], data)),
    }



  #
  # Parsing Output
  #


  def __parse_dataframes(self, dataframes):
    '''
      Pre-parsing for the dataframes fetched by `fetch_input`.
      The results of this function are used to parse both the "input" and the "output" values.
    '''

    # Convert dataframes to dicts, mapping strain column to trait value column
    data = tuple(map(
      lambda df: dataframe_cols_to_dict(df, 'strain_name', 'trait_value', drop_na=True), dataframes
    ))

    # Get the list of strains in both datasets by taking the intersection of their key sets
    # Convert back to a list because sets ~technically~ don't have a defined order -- we want to make sure
    # the list of strains is the same each time we use it
    data_keys = list( keyset_intersection(*data) )

    # Filter each dataset down to just the strains in the overlapping set, in the same order computed above
    data_vals = tuple([
      [ d[strain] for strain in data_keys ] for d in data
    ])

    return {
      'data_keys': data_keys,
      'data_vals': data_vals,
    }


  def _parse_output(self, data):

    if data is None:
      raise EmptyReportResultsError(self.report.id)

    # Parse the dataframes
    data = self.__parse_dataframes(data)

    # Zip the trait values together with the strain names, to get the full dataset array
    data_tuples = list(zip(*data['data_vals'], data['data_keys']))

    # Compute the Spearman Coefficient for the given data, if two traits are being compared
    if len(data['data_vals']) == 2:
      res = stats.spearmanr(data['data_vals'][0], data['data_vals'][1])
    else:
      res = None

    # Return the relevant values
    return {
      'correlation': res.correlation if res else None,
      'p_value':     res.pvalue      if res else None,
      'trait_values': data_tuples,
    }



  #
  # Run Configuration
  #
  # These are required by the parent class, but this pipeline doesn't use a Runner,
  # so all functions can return empty values
  #

  def construct_command(self):
    return []

  def construct_environment(self):
    return {}

  def construct_run_params(self):
    return {}
