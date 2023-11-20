import csv

from caendr.services.logger import logger

from caendr.models.error import DataFormatError
from caendr.api.strain   import query_strains
from caendr.api.isotype  import get_distinct_isotypes
from caendr.utils.data   import get_file_format, join_commas_and
from caendr.utils.env    import get_env_var



INDEL_PRIMER_CONTAINER_NAME = get_env_var('INDEL_PRIMER_CONTAINER_NAME')
HERITABILITY_CONTAINER_NAME = get_env_var('HERITABILITY_CONTAINER_NAME')
NEMASCAN_NXF_CONTAINER_NAME = get_env_var('NEMASCAN_NXF_CONTAINER_NAME')



def get_delimiter_from_filepath(filepath=None, valid_file_extensions=None):
  valid_file_extensions = valid_file_extensions or {'csv'}
  if filepath:
    file_format = get_file_format(filepath[-3:], valid_formats=valid_file_extensions)
    if file_format:
      return file_format['sep']



def validate_file(local_path_or_file, columns, delimiter='\t', unique_rows=False):

  num_cols = len(columns)
  rows = {}

  # Read first line from tsv
  with open(local_path_or_file, 'r', encoding='utf-8-sig') as f:
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
    for col in range(num_cols):
      target_header = columns[col].get('header')
      if target_header is None:
        continue
      # if isinstance(target_header, str):
      if csv_headings[col] != target_header:
        invalid_headers.append(col)
      # else:
      #   if not target_header['validator'](csv_headings[col]):
      #     raise DataFormatError(f'The file contains an incorrect column header. { target_header["make_err_msg"]( col + 1, csv_headings[col] ) }', 1)

    # If one header was incorrect, flag it
    if len(invalid_headers) == 1:
      col = invalid_headers[0]
      raise DataFormatError(f'The file contains an incorrect column header. Column #{ col + 1 } should be { columns[col]["header"] }.', 1)

    # If multiple headers were incorrect, flag all of them at once
    elif len(invalid_headers) > 1:
      cs = join_commas_and([ f'#{c + 1}' for c in invalid_headers ])
      hs = join_commas_and([ c["header"] for c in columns ])
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

      # Check that all columns have valid data, using the "step" validator
      for column, value in zip(columns, csv_row):
        header    = column.get('header')
        validator = column['validator']
        if 'step' in validator:
          validator['step']( header, value.strip(), line )

      # Track that we parsed at least one line of data properly
      has_data = True

    # Check that the loop ran at least once (i.e. is not just headers)
    if not has_data:
      raise DataFormatError('The file is empty. Please edit the file to include your data.')

    # Run each validator's "final" function at the end, in case any of the "step" validators were accumulating values
    for c in columns:
      if 'final' in c['validator']:
        c['validator']['final']()



#
# Validator Functions
#

def validate_num(accept_float = False, accept_na = False):

  # Construct a message for the expected data type
  if accept_float:
    data_type = 'decimal'
  else:
    data_type = 'integer'

  # Define the validator function
  def func(header, value, line):
    nonlocal data_type

    # Try casting the value to the appropriate num type
    try:
      if accept_float:
        float(value)
      else:
        int(value)

    # If casting fails, raise an error (with an exception for 'NA', if applicable)
    except:
      if not (accept_na and value == 'NA'):
        raise DataFormatError(f'Column { header } is not a valid { data_type }. Please edit { header } to ensure only { data_type } values are included.', line)

  return { 'step': func }



# Check that column is a valid strain name for the desired species
def validate_strain(species, force_unique=False, force_unique_msgs=None):

  # Get the list of all valid strain names for this species
  # Pull from strain names & isotype names, to allow for isotypes with no strain of the same name
  valid_names_species = {
    *query_strains(all_strain_names=True, species=species.name),
    *get_distinct_isotypes(species=species.name),
  }

  # Get the list of all valid strain names for all species
  # Used to provide more informative error messages
  valid_names_all = {
    *query_strains(all_strain_names=True),
    *get_distinct_isotypes(),
  }

  # Dict to track the first line each strain occurs on
  # Used to ensure strains are unique, if applicable
  strain_line_numbers = {}

  problems = {
    'blank_line':     [],
    'wrong_species':  [],
    'unknown_strain': [],
    'duplicates':     [],
  }


  def check_strain_list(problem_list, err_messages):
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
  def func_final():
    nonlocal force_unique_msgs
    nonlocal problems

    # Wrong species #
    check_strain_list(problems['wrong_species'], {
      'single':  lambda x: f'The strain { x } is not a valid strain for { species.short_name } in our current dataset. Please enter a valid { species.short_name } strain.',
      'few':     lambda x: f'The strains { x } are not valid strains for { species.short_name } in our current dataset. Please enter valid { species.short_name } strains.',
      'default': lambda x: f'Multiple strains are not valid for { species.short_name } in our current dataset.',
    })

    # Blank lines #
    if len(problems['blank_line']) > 0:
      line_str = join_commas_and([ p['line'] for p in problems['blank_line'] ])
      raise DataFormatError(f'Strain values cannot be blank. Please check line(s) { line_str } to ensure valid strains have been entered.')

    # Unknown strains #
    check_strain_list(problems['unknown_strain'], {
      'single':  lambda x: f'The strain { x } is not a valid strain name in our current dataset. Please enter valid strain names.',
      'few':     lambda x: f'The strains { x } are not valid strain names in our current dataset. Please enter valid strain names.',
      'default': lambda x: f'Multiple strains are not valid in our current dataset.',
    })

    # Duplicate strains #
    check_strain_list(problems['duplicates'], force_unique_msgs or {
      'single':  lambda x: f'Multiple lines contain duplicate values for the strain { x }. Please ensure that only one unique value exists per strain.',
      'default': lambda x: f'Multiple lines contain duplicate values for the same strain. Please ensure that only one unique value exists per strain.',
    })


  # Validator function run on each individual line
  # Keeps track of all errors, which are then run at the end by func_final
  def func_step(header, value, line):
    nonlocal force_unique
    nonlocal strain_line_numbers, valid_names_species, valid_names_all, problems

    # Check for blank strain
    if value == '':
      problems['blank_line'].append({'value': value, 'line': line})

    # Check if strain is valid for the desired species
    elif value not in valid_names_species:
      if value in valid_names_all:
        problems['wrong_species'].append({'value': value, 'line': line})
      else:
        problems['unknown_strain'].append({'value': value, 'line': line})

    # If desired, keep track of list of strains and throw an error if a duplicate is found
    if force_unique:
      if value in strain_line_numbers:
        problems['duplicates'].append({'value': value, 'line': line})
      else:
        strain_line_numbers[value] = line


  # Return both validator functions
  return {
    'step': func_step,
    'final': func_final,
  }



# Check that all values in a column have the same trait name
def validate_trait():

  # Initialize var to track the single valid trait name
  trait_name = None

  # Define the validator function
  def func(header, value, line):
    nonlocal trait_name

    # If no trait name has been encountered yet, save the first value
    if trait_name is None:
      trait_name = value

    # If the trait name has been set, ensure this line matches it
    elif value != trait_name:
      raise DataFormatError(f'The data contain multiple unique trait name values. Only one trait name may be tested per file.', line)

  return { 'step': func }
