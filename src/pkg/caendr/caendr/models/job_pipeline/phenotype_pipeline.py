from scipy import stats

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import PhenotypeReport

# Services
from caendr.models.datastore       import TraitFile
from caendr.models.error           import EmptyReportDataError, EmptyReportResultsError
from caendr.models.status          import JobStatus
from caendr.utils.data             import dataframe_cols_to_dict, get_object_hash



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
    data_1 = dataframe_cols_to_dict(dataframes[0], 'strain_name', 'trait_value', drop_na=True)
    data_2 = dataframe_cols_to_dict(dataframes[1], 'strain_name', 'trait_value', drop_na=True)

    # Get the list of strains in both datasets by taking the intersection of their key sets
    # Convert back to a list because sets ~technically~ don't have a defined order -- we want to make sure
    # the list of strains is the same each time we use it
    overlap_strains = list( set(data_1.keys()).intersection(data_2.keys()) )

    # From each dataset, get a list of trait values for each strain in the overlapping set
    x = [ data_1[strain] for strain in overlap_strains ]
    y = [ data_2[strain] for strain in overlap_strains ]

    return {
      'dataframes': (data_1, data_2),
      'data_keys':  overlap_strains,
      'data_vals':  (x, y),
    }


  def _parse_output(self, data):

    if data is None:
      raise EmptyReportResultsError(self.report.id)

    # Parse the dataframes
    data = self.__parse_dataframes(data)

    # Rename trait value arrays, for convenience
    x, y = data['data_vals'][0], data['data_vals'][1]

    # Zip the trait values together with the strain names, to get the full dataset array
    data_tuples = list(zip(x, y, data['data_keys']))

    # Compute the Spearman Coefficient for the given data
    res = stats.spearmanr(data['data_vals'][0], data['data_vals'][1])

    # Return the relevant values
    return {
      'correlation': res.correlation,
      'p_value':     res.pvalue,
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
