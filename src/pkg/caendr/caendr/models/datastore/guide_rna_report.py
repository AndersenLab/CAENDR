from typing import Tuple

from caendr.models.datastore import ReportEntity, HashableEntity
from caendr.services.guide_rna_selection import get_grna_selection_enzymes



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


  def _make_download_name(self) -> str:
    return f'{self["species"]}_{ "_".join(self.strains) }_{self["site"]}'



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


  def serialize(self, **kwargs):
    return {
      **super().serialize(**kwargs),
      'enzyme_display': self.enzyme_display,
    }



  @property
  def strains(self) -> Tuple[str]:
    if self['strain_2']:
      return (self['strain_1'], self['strain_2'])
    else:
      return (self['strain_1'],)

  @property
  def enzyme_display(self):
    return get_grna_selection_enzymes().get(self['enzyme'], '')
