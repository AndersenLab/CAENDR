from typing import Tuple

from caendr.models.datastore import ReportEntity, HashableEntity, TraitFile
from caendr.models.trait     import Trait



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
    return tuple(self.traits)

  def fetch_output(self):
    return tuple( trait.query_values_dataframe() for trait in self.traits )



  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
      'trait_1',
      'trait_1_name',
      'trait_2',
      'trait_2_name',
    }


  #
  # Trait File 1
  #

  @property
  def trait_1(self) -> TraitFile:

    # Name will always exist if set, so if not found, return None
    if not getattr(self, '_trait_1_id', ''):
      return None

    # If the corresponding file object is not cached yet, retrieve it
    if getattr(self, '_trait_1_file', None) is None:
      self._trait_1_file = TraitFile.get_ds(self._trait_1_id)

    # Return the TraitFile entity object itself
    return self._trait_1_file


  @trait_1.setter
  def trait_1(self, val):

    # If passing TraitFile entity name, save as-is
    if val is None or isinstance(val, str):
      self._trait_1_id   = val
      self._trait_1_file = None

    # If passing TraitFile object itself, save both name and value
    elif isinstance(val, TraitFile):
      self._trait_1_id   = val.name
      self._trait_1_file = val

    # Otherwise, raise an error
    else:
      raise TypeError(f'Cannot set trait_1 to "{ val }"')


  @property
  def has_trait_1(self) -> bool:
    return bool(self._trait_1_id)


  #
  # Trait File 2
  #

  @property
  def trait_2(self) -> TraitFile:

    # Name will always exist if set, so if not found, return None
    if not getattr(self, '_trait_2_id', ''):
      return None

    # If the corresponding file object is not cached yet, retrieve it
    if getattr(self, '_trait_2_file', None) is None:
      self._trait_2_file = TraitFile.get_ds(self._trait_2_id)

    # Return the TraitFile entity object itself
    return self._trait_2_file

  @trait_2.setter
  def trait_2(self, val):

    # If passing TraitFile entity name, save as-is
    if val is None or isinstance(val, str):
      self._trait_2_id   = val
      self._trait_2_file = None

    # If passing TraitFile object itself, save both name and value
    elif isinstance(val, TraitFile):
      self._trait_2_id   = val.name
      self._trait_2_file = val

    # Otherwise, raise an error
    else:
      raise TypeError(f'Cannot set trait_2 to "{ val }"')


  @property
  def has_trait_2(self) -> bool:
    return bool(self._trait_2_id)


  #
  # Trait Names
  #
  # TODO: Is there a smarter way to determine when to check the TraitFile object?
  #       Since we're duplicating the trait name from the TraitFile, it would be nice to validate it,
  #       but if we do so every time we use the param, we spam the datastore with requests and cause
  #       certain pages (namely my-results and all-results) to take a long time to load
  #

  # @property
  # def trait_1_name(self) -> str:

  #   # Retrieve the stored value from this entity
  #   local_value = self._get_raw_prop('trait_1_name')

  #   # Look up the value specified in the trait file, if applicable
  #   if self.has_trait_1 and not self['trait_1']['is_bulk_file']:
  #     trait_file_value = self['trait_1']['trait_name_caendr']
  #   else:
  #     trait_file_value = None

  #   # If no value is stored but the trait file is bulk, we can't uniquely identify the trait
  #   if local_value is None and self['trait_1']['is_bulk_file']:
  #     raise LookupError(f'Trait name is ambiguous: trait_1 field references a bulk file, but no specific trait name is given')

  #   # If no value stored, defer to trait file
  #   if local_value is None:
  #     local_value = trait_file_value

  #   # If values don't match, raise an error
  #   if trait_file_value is not None and local_value != trait_file_value:
  #     raise LookupError(f'Trait name mismatch: trait_1 file has name {trait_file_value}, but Report entity is storing name {local_value}')

  #   # Return the local value
  #   return local_value


  # @trait_1_name.setter
  # def trait_1_name(self, val):

  #   # If trait file already specifies a name, make sure they match, then ignore the set
  #   if self['trait_1'] is not None and not self['trait_1']['is_bulk_file']:
  #     if val != self['trait_1']['trait_name_caendr']:
  #       raise ValueError(f'Cannot set trait_1 name to {val}: trait file already specifies the name as {self["trait_1"]["trait_name_caendr"]}')

  #   # Otherwise, add the name
  #   else:
  #     self._set_raw_prop('trait_1_name', val)


  # @property
  # def trait_2_name(self) -> str:

  #   if not self.has_trait_2:
  #     return None

  #   # Retrieve the stored value from this entity
  #   local_value = self._get_raw_prop('trait_2_name')

  #   # Look up the value specified in the trait file, if applicable
  #   if self.has_trait_2 and not self['trait_2']['is_bulk_file']:
  #     trait_file_value = self['trait_2']['trait_name_caendr']
  #   else:
  #     trait_file_value = None

  #   # If no value is stored but the trait file is bulk, we can't uniquely identify the trait
  #   if local_value is None and self['trait_2']['is_bulk_file']:
  #     raise LookupError(f'Trait name is ambiguous: trait_2 field references a bulk file, but no specific trait name is given')

  #   # If no value stored, defer to trait file
  #   if local_value is None:
  #     local_value = trait_file_value

  #   # If values don't match, raise an error
  #   if trait_file_value is not None and local_value != trait_file_value:
  #     raise LookupError(f'Trait name mismatch: trait_2 file has name {trait_file_value}, but Report entity is storing name {local_value}')

  #   # Return the local value
  #   return local_value


  # @trait_2_name.setter
  # def trait_2_name(self, val):

  #   # If trait file already specifies a name, make sure they match, then ignore the set
  #   if self['trait_2'] is not None and not self['trait_2']['is_bulk_file']:
  #     if val != self['trait_2']['trait_name_caendr']:
  #       raise ValueError(f'Cannot set trait_2 name to {val}: trait file already specifies the name as {self["trait_2"]["trait_name_caendr"]}')

  #   # Otherwise, add the name
  #   else:
  #     self._set_raw_prop('trait_2_name', val)



  #
  # Traits grouped
  #

  @property
  def traits(self) -> Tuple[Trait]:
    return tuple(
      Trait.from_datastore(file, name) for file, name in zip(self.trait_files, self.trait_names)
    )

  @property
  def trait_files(self) -> Tuple[TraitFile]:
    if self['trait_2'] is None:
      return self['trait_1'],
    return self['trait_1'], self['trait_2']

  @property
  def trait_names(self) -> Tuple[str]:
    if self['trait_2'] is None:
      return self['trait_1_name'],
    return self['trait_1_name'], self['trait_2_name']
