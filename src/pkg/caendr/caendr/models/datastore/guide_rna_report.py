from caendr.models.datastore import ReportEntity, HashableEntity



class GuideRNAReport(ReportEntity, HashableEntity):
  kind = 'guide_rna_report'


  #
  # Class Variables
  #

  _report_display_name = 'gRNA site'
  _data_id_field       = 'data_hash'

  # TODO: Set data hash from trait files? Unique names / IDs?



  #
  # Input & Output
  #
  # TODO: Accept input files(?) to create a report
  #

  _num_input_files = 0
  _input_filename  = None
  _output_filename = None


  def fetch_input(self):
    return self.serialize()

  def fetch_output(self):
    return {}



  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
      'release',

      # Query
      'enzyme',
      'site',
      'strain_1',
      'strain_2',
    }
