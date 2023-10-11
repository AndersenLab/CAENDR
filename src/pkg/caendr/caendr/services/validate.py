import csv

from caendr.services.logger import logger

from caendr.models.error import DataFormatError
from caendr.api.strain   import query_strains
from caendr.api.isotype  import get_distinct_isotypes
from caendr.utils.data   import get_file_format
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



def validate_file(local_path, columns, delimiter='\t', unique_rows=False):

  num_cols = len(columns)
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
    for col in range(num_cols):
      target_header = columns[col].get('header')
      if target_header is None:
        continue
      # if isinstance(target_header, str):
      if csv_headings[col] != target_header:
        raise DataFormatError(f'The file contains an incorrect column header. Column #{ col + 1 } should be { columns[col]["header"] }.', 1)
      # else:
      #   if not target_header['validator'](csv_headings[col]):
      #     raise DataFormatError(f'The file contains an incorrect column header. { target_header["make_err_msg"]( col + 1, csv_headings[col] ) }', 1)

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
      for column, value in zip(columns, csv_row):
        header    = column.get('header')
        validator = column['validator']
        validator( header, value.strip(), line )

      # Track that we parsed at least one line of data properly
      has_data = True

    # Check that the loop ran at least once (i.e. is not just headers)
    if not has_data:
      raise DataFormatError('The file is empty. Please edit the file to include your data.')



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

  return func


# Check that column is a valid strain name for the desired species
def validate_strain(species, force_unique=False, force_unique_msg=None):

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

  # Provide a default message if the same strain is found more than once
  # Only used if force_unique is True and if the calling function doesn't customize this message
  if force_unique_msg is None:
    force_unique_msg = lambda prev_line, curr_line: \
      f'Lines #{ prev_line } and #{ curr_line } contain duplicate values for the same strain. Please ensure that only one unique value exists per strain.'

  # Define the validator function
  def func(header, value, line):
    nonlocal force_unique, force_unique_msg
    nonlocal strain_line_numbers, valid_names_species, valid_names_all

    # Check for blank strain
    if value == '':
      raise DataFormatError(f'Strain values cannot be blank. Please check line { line } to ensure a valid strain has been entered.', line)

    # Check if strain is valid for the desired species
    if value not in valid_names_species:
      if value in valid_names_all:
        raise DataFormatError(f'The strain { value } is not a valid strain for { species.short_name } in our current dataset. Please enter a valid { species.short_name } strain.', line)
      else:
        raise DataFormatError(f'The strain { value } is not a valid strain name in our current dataset. Please ensure that { value } is valid.', line)

    # If desired, keep track of list of strains and throw an error if a duplicate is found
    if force_unique:
      if value in strain_line_numbers:
        raise DataFormatError(force_unique_msg(prev_line=strain_line_numbers[value], curr_line=line))
      strain_line_numbers[value] = line

  return func


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

  return func
