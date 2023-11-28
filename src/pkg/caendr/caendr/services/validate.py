from abc import ABC, abstractmethod
import csv
from typing import Callable, Optional, Union

from caendr.models.error import DataFormatError
from caendr.api.strain   import query_strains
from caendr.api.isotype  import get_distinct_isotypes
from caendr.utils.data   import join_commas_and



def validate_file(local_path, validators, delimiter='\t', unique_rows=False):

  num_cols = len(validators)
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
    for col, (validator, header) in enumerate(zip(validators, csv_headings)):
      if not validator.read_header(header):
        invalid_headers.append(col)

    # If one header was incorrect, flag it
    if len(invalid_headers) == 1:
      col = invalid_headers[0]
      raise DataFormatError(f'The file contains an incorrect column header. Column #{ col + 1 } should be { validators[col].expected_header }.', 1)

    # If multiple headers were incorrect, flag all of them at once
    elif len(invalid_headers) > 1:
      cs = join_commas_and([ f'#{c + 1}' for c in invalid_headers ])
      hs = join_commas_and([ c.expected_header for c in validators ])
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

      # Check that all columns have valid data
      for validator, value in zip(validators, csv_row):
        validator.read_line( value.strip(), line )

      # Track that we parsed at least one line of data properly
      has_data = True

    # Check that the loop ran at least once (i.e. is not just headers)
    if not has_data:
      raise DataFormatError('The file is empty. Please edit the file to include your data.')

    # Run each validator's "finish" function at the end, in case any of the "read_line" validators were accumulating values
    for validator in validators:
      validator.finish()




#
# Validator Base Class
#

class ColumnValidator(ABC):

  #
  # Instantiation
  #

  def __init__(self, valid_header: Optional[Union[str, Callable[[str], bool]]]):

    # Initilize stored header value to None
    self._header = None

    # If string, create validator function that checks equality
    if isinstance(valid_header, str):
      self._validate_header = lambda x: x == valid_header
      self.expected_header = f'"{valid_header}"'

    # If None, create validator function that always succeeds
    elif valid_header is None:
      self._validate_header = lambda _: True
      self.expected_header = '(any)'

    # If callable, use the value itself as the validator function
    elif callable(valid_header):
      self._validate_header = valid_header

    # Otherwise, raise error
    else:
      raise ValueError(f'Header argument must be a string, a callable, or None, but received "{valid_header}"')



  #
  # Header
  #

  @property
  def header(self):
    '''
      The validated header value for this column.
      If no header has been read yet, will be `None`.
    '''
    return self._header

  def read_header(self, header):
    '''
      Validate and store the header value for this column.
    '''
    if not self._validate_header(header):
      return False
    self._header = header
    return True


  #
  # Validators
  #

  @abstractmethod
  def read_line(self, value, line):
    '''
      Parse and validate a single line.
      Can raise errors here, or record them to raise all at once in `finish()`.

      Arguments:
        value:  The value in the current line, to be validated.
        line:   The index of the current line.
    '''
    pass

  def finish(self):
    '''
      Called at the end of the file.
    '''
    pass



#
# Numeric Values
#

class NumberValidator(ColumnValidator):
  '''
    Validator for numeric values.
  '''

  def __init__(self, *args, accept_float = False, accept_na = False, **kwargs):
    super().__init__(*args, **kwargs)

    self.accept_float = accept_float
    self.accept_na    = accept_na

  @property
  def data_type(self):
    '''
      Construct a message for the expected data type
    '''
    return 'decimal' if self.accept_float else 'integer'

  def read_line(self, value, line):

    # Try casting the value to the appropriate num type
    try:
      if self.accept_float:
        float(value)
      else:
        int(value)

    # If casting fails, raise an error (with an exception for 'NA', if applicable)
    except:
      if not (self.accept_na and value == 'NA'):
        raise DataFormatError(f'Column { self.header } is not a valid { self.data_type }. Please edit { self.header } to ensure only { self.data_type } values are included.', line)



#
# Strains
#

class StrainValidator(ColumnValidator):
  '''
    Check that column is a valid strain name for the desired species.
  '''

  def __init__(self, *args, species, force_unique=False, force_unique_msgs=None, **kwargs):
    super().__init__(*args, **kwargs)

    # Store species value
    self.species = species

    # Store uniqueness values
    self._force_unique      = force_unique
    self._force_unique_msgs = force_unique_msgs

    # Get the list of all valid strain names for this species
    # Pull from strain names & isotype names, to allow for isotypes with no strain of the same name
    self._valid_names_species = {
      *query_strains(all_strain_names=True, species=species.name),
      *get_distinct_isotypes(species=species.name),
    }

    # Get the list of all valid strain names for all species
    # Used to provide more informative error messages
    self._valid_names_all = {
      *query_strains(all_strain_names=True),
      *get_distinct_isotypes(),
    }

    # Dict to track the first line each strain occurs on
    # Used to ensure strains are unique, if applicable
    self._strain_line_numbers = {}

    self._problems = {
      'blank_line':     [],
      'wrong_species':  [],
      'unknown_strain': [],
      'duplicates':     [],
    }


  @classmethod
  def check_strain_list(cls, problem_list, err_messages):
    '''
      Given a list of lines that matched a specific error condition, collate the unique set of strains and create an error message.
      If the list is empty, no error will be thrown.

      Arguments:
        - problem_list (list): The list of values matching the error condition. Each entry should be a dict with the field 'value' containing the strain name.
        - err_messages (dict): A dict of functions for turning one or more strain names into an error message. Valid keys:
            - single:  Called when one strain matches the error condition.
            - few:     Called when 2-3 strains match the error condition. Can be used to display a short list of names inline, rather than in a dropdown.
            - default: REQUIRED. Called when 4+ strains match the error condition, OR as a fallback if any of the above functions are not defined.

      Returns:
        None, if validation succeeded

      Throws:
        DataFormatError, containing the appropriate error message.  If strain list was longer than 4 elements, will contain full list in the full_msg_* fields.

      NOTE: The `err_messages` dict MUST contain a key "default", as this is the final fallback value.
            If other keys are omitted, this function will be used.
    '''
    truncate_length = 3

    if not err_messages.get('default'):
      raise ValueError('The "err_messages" dict must contain a key "default".')

    prob_strains = []
    for s in problem_list:
      if s['value'] not in prob_strains:
        prob_strains.append(s['value'])
    num_problems = len(prob_strains)

    if err_messages.get('single') and (num_problems == 1):
      raise DataFormatError( err_messages['single'](prob_strains[0]) )

    elif err_messages.get('few') and (1 < num_problems <= truncate_length):
      prob_str = join_commas_and(prob_strains)
      raise DataFormatError( err_messages['few'](prob_str) )

    elif 1 <= num_problems:
      prob_str = join_commas_and(prob_strains, truncate=truncate_length)
      raise DataFormatError(
        err_messages['default'](prob_str),
        full_msg_link='View the full list of strains.',
        full_msg_body=', '.join(prob_strains),
      )


  # Validator function run at the end of the file
  def finish(self):

    # Wrong species #
    self.check_strain_list(self._problems['wrong_species'], {
      'single':  lambda x: f'The strain { x } is not a valid strain for { self.species.short_name } in our current dataset. Please enter a valid { self.species.short_name } strain.',
      'few':     lambda x: f'The strains { x } are not valid strains for { self.species.short_name } in our current dataset. Please enter valid { self.species.short_name } strains.',
      'default': lambda x: f'Multiple strains are not valid for { self.species.short_name } in our current dataset.',
    })

    # Blank lines #
    if len(self._problems['blank_line']) > 0:
      line_str = join_commas_and([ p['line'] for p in self._problems['blank_line'] ])
      raise DataFormatError(f'Strain values cannot be blank. Please check line(s) { line_str } to ensure valid strains have been entered.')

    # Unknown strains #
    self.check_strain_list(self._problems['unknown_strain'], {
      'single':  lambda x: f'The strain { x } is not a valid strain name in our current dataset. Please enter valid strain names.',
      'few':     lambda x: f'The strains { x } are not valid strain names in our current dataset. Please enter valid strain names.',
      'default': lambda x: f'Multiple strains are not valid in our current dataset.',
    })

    # Duplicate strains #
    self.check_strain_list(self._problems['duplicates'], self._force_unique_msgs or {
      'single':  lambda x: f'Multiple lines contain duplicate values for the strain { x }. Please ensure that only one unique value exists per strain.',
      'default': lambda x: f'Multiple lines contain duplicate values for the same strain. Please ensure that only one unique value exists per strain.',
    })


  # Validator function run on each individual line
  # Keeps track of all errors, which are then run at the end by func_final
  def read_line(self, value, line):

    # Check for blank strain
    if value == '':
      self._problems['blank_line'].append({'value': value, 'line': line})

    # Check if strain is valid for the desired species
    elif value not in self._valid_names_species:
      if value in self._valid_names_all:
        self._problems['wrong_species'].append({'value': value, 'line': line})
      else:
        self._problems['unknown_strain'].append({'value': value, 'line': line})

    # If desired, keep track of list of strains and throw an error if a duplicate is found
    if self._force_unique:
      if value in self._strain_line_numbers:
        self._problems['duplicates'].append({'value': value, 'line': line})
      else:
        self._strain_line_numbers[value] = line



#
# Traits
#

class TraitValidator(ColumnValidator):
  '''
    Check that all values in a column have the same trait name
  '''

  def __init__(self, *args, trait_name: str = None, **kwargs):
    super().__init__(*args, **kwargs)

    # Initialize var to track the single valid trait name
    self._trait_name = trait_name


  def read_line(self, value, line):
    '''
      Ensure all lines contain the same trait value.
    '''

    # If no trait name has been encountered yet, save the first value
    if self._trait_name is None:
      self._trait_name = value

    # If the trait name has been set, ensure this line matches it
    elif value != self._trait_name:
      raise DataFormatError(f'The data contain multiple unique trait name values. Only one trait name may be tested per file.', line)
