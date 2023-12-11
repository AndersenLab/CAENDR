import pandas as pd

from caendr.models.datastore          import ReportEntity, HashableEntity, TraitFile
from caendr.models.sql                import PhenotypeDatabase
from caendr.services.cloud.postgresql import db



class PhenotypeReport(ReportEntity, HashableEntity):
  kind = 'phenotype_report'


  #
  # Class Variables
  #

  _report_display_name = 'Phenotype'
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
    return self.trait_files

  def fetch_output(self):
    return tuple([
      pd.read_sql_query(
        PhenotypeDatabase.query.filter( PhenotypeDatabase.trait_name == tf['trait_name'] ).statement, con=db.engine
      )
        for tf in self.trait_files
    ])



  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
      'label',
      'trait_1',
      'trait_2',
    }


  #
  # Trait File 1
  #

  @property
  def trait_1(self) -> TraitFile:

    # Name will always exist if set, so if not found, return None
    if not getattr(self, '_trait_1_name', ''):
      return None

    # If the corresponding file object is not cached yet, retrieve it
    if getattr(self, '_trait_1_file', None) is None:
      self._trait_1_file = TraitFile.get_ds(self._trait_1_name)

    # Return the TraitFile entity object itself
    return self._trait_1_file


  @trait_1.setter
  def trait_1(self, val):

    # If passing TraitFile entity name, save as-is
    if isinstance(val, str):
      self._trait_1_name = val
      self._trait_1_file = None

    # If passing TraitFile object itself, save both name and value
    elif isinstance(val, TraitFile):
      self._trait_1_name = val.name
      self._trait_1_file = val

    # Otherwise, raise an error
    else:
      raise TypeError(f'Cannot set trait_1 to "{ val }"')


  #
  # Trait File 2
  #

  @property
  def trait_2(self) -> TraitFile:

    # Name will always exist if set, so if not found, return None
    if not getattr(self, '_trait_2_name', ''):
      return None

    # If the corresponding file object is not cached yet, retrieve it
    if getattr(self, '_trait_2_file', None) is None:
      self._trait_2_file = TraitFile.get_ds(self._trait_2_name)

    # Return the TraitFile entity object itself
    return self._trait_2_file

  @trait_2.setter
  def trait_2(self, val):

    # If passing TraitFile entity name, save as-is
    if isinstance(val, str):
      self._trait_2_name = val
      self._trait_2_file = None

    # If passing TraitFile object itself, save both name and value
    elif isinstance(val, TraitFile):
      self._trait_2_name = val.name
      self._trait_2_file = val

    # Otherwise, raise an error
    else:
      raise TypeError(f'Cannot set trait_2 to "{ val }"')


  #
  # Trait Names
  #

  @property
  def trait_1_name(self) -> str:
    return self['trait_1']['trait_name']

  @property
  def trait_2_name(self) -> str:
    return self['trait_2']['trait_name']

  @property
  def trait_files(self):
    if self['trait_2'] is None:
      return self['trait_1']
    return self['trait_1'], self['trait_2']
