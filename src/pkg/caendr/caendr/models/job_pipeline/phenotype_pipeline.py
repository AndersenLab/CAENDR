from scipy import stats

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import PhenotypeReport

# Services
from caendr.utils.data             import dataframe_cols_to_dict



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


  #
  # Parsing Submission
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):
    return super().parse(data, valid_file_extensions=valid_file_extensions)



  #
  # Fetching Overwrites
  #
  # Rewrite the logic so `fetch` is the source of truth and input/output take slices,
  # rather than the other way around.
  #
  # For the phenotype tool, there are no distinct input/output files,
  # just the source of trait data -- all "results" are computed here.
  #
  # Since input and output both rely on the same parsed data, we factor out that parsing
  # and have the respective parse functions both act on the *same* data.
  # The distinction between the two is mostly semantic -- splitting them this way makes a
  # difference for calling functions, even if under the hood they're largely handled the same
  #

  def fetch(self, raw: bool = False):
    raw_data = self.report.fetch_input()

    if raw or raw_data is None:
      return raw_data, None

    parsed_data = self.__parse_dataframes(raw_data)
    return self._parse_input(parsed_data), self._parse_output(parsed_data)


  def fetch_input(self, raw: bool = False):
    return self.fetch(raw=raw)[0]

  def fetch_output(self, raw: bool = False):
    return self.fetch(raw=raw)[1]



  #
  # Parsing Input & Output
  #


  def __parse_dataframes(self, dataframes):
    '''
      Pre-parsing for the dataframes fetched by `fetch_input`.
      The results of this function are used to parse both the "input" and the "output" values.
    '''

    # Convert dataframes to dicts, mapping strain column to trait value column
    data_1 = dataframe_cols_to_dict(dataframes[0], 'strain', 1, drop_na=True)
    data_2 = dataframe_cols_to_dict(dataframes[1], 'strain', 1, drop_na=True)

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



  def _parse_input(self, data):

    # Rename trait value arrays, for convenience
    x, y = data['data_vals'][0], data['data_vals'][1]

    # Zip the trait values together with the strain names, to get the full dataset array
    data_tuples = list(zip(x, y, data['data_keys']))

    # Return trait names and trait values
    return {
      'trait_names':  (self.report['trait_1']['trait_name'], self.report['trait_2']['trait_name']),
      'trait_values': data_tuples,
    }


  def _parse_output(self, data):

    # Compute the Spearman Coefficient for the given data
    res = stats.spearmanr(data['data_vals'][0], data['data_vals'][1])
  
    # Return the relevant values
    return {
      'correlation': res.correlation,
      'p_value':     res.pvalue,
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
