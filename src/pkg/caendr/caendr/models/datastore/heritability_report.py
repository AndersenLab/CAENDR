from caendr.models.datastore import DataJobEntity


H2_REPORT_PATH_PREFIX = 'reports'
H2_INPUT_FILE = 'data.tsv'
H2_RESULT_FILE = 'heritability_result.tsv'


class HeritabilityReport(DataJobEntity):
  kind = 'heritability_report'
  _blob_prefix = H2_REPORT_PATH_PREFIX
  _input_file  = H2_INPUT_FILE
  _result_file = H2_RESULT_FILE


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

      # Query
      'label',
      'trait',
    }
