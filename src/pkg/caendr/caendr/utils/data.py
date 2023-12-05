import yaml
import hashlib
import uuid
import string
import pandas as pd

from collections import Counter
from caendr.services.logger import logger

from caendr.utils.constants import DEFAULT_BATCH_SIZE



class AltTemplate(string.Template):
  delimiter = '%'

def flatten_dict(d, max_depth=1):
  '''  Flattens nested dictionaries '''
  def expand(key, value):
    if hasattr(value, "__dict__"):
      value = value.__dict__
      print(value)
    if isinstance(value, dict) and max_depth > 0:
      return [(key + '.' + k, v) for k, v in flatten_dict(value, max_depth - 1).items()]
    else:
      return [(key, value)]

  items = [item for k, v in d.items() for item in expand(k, v)]

  return dict(items)


# TODO: remove static/yaml files
def load_yaml(yaml_file):
  return yaml.safe_load(open(f"base/static/yaml/{yaml_file}", 'r'))


def get_object_hash(object, length=10):
  ''' Generates the sha1 hash of an object encoded as a string and returns the first 'length' characters '''
  return hashlib.sha1(str(object).encode('utf-8')).hexdigest()[0:length]


def get_password_hash(password):
  ''' Generates the md5 hash of a password '''
  h = hashlib.md5(str(password).encode())
  return h.hexdigest()


def unique_id():
  ''' Generates a new hexadecimal UUID4 '''
  return uuid.uuid4().hex


def is_number(s):
  ''' Returns true if the variable is an int, long, float, or complex number '''
  if not s:
    return None
  try:
    complex(s)  # for int, long, float and complex
  except (ValueError, TypeError):
    return False

  return True


def list_duplicates(input_list):
  """ Return the set of duplicate values in a list """
  counts = Counter(input_list)
  return [x for x, v in counts.items() if v > 1]


def coalesce(*values):
  """Return the first non-None value or None if all values are None"""
  return next((v for v in values if v is not None), None)


def convert_query_to_data_table(query, columns):
  """
    Convert a Flask SQLAlchemy query into a Pandas DataFrame.
  """
  return pd.DataFrame(
    ({ col: getattr(row, col) for col in columns } for row in query.all()), columns=columns
  )


def convert_data_to_download_file(data, columns, file_ext='csv'):

  # Interpret the desired output file format
  format_params = get_file_format(file_ext)
  if format_params is None:
    raise ValueError(f'Cannot convert data to file format "{file_ext}".')

  # Convert to DataFrame, then to CSV
  return pd.DataFrame(data, columns=columns).to_csv(index=False, sep=format_params['sep'])


def get_file_format(file_ext, valid_formats=None):

  # Screen out invalid formats
  if valid_formats is not None and file_ext not in valid_formats:
    return None

  # Check possible file extensions
  if file_ext == 'csv':
    return {
      'sep':      ',',
      'mimetype': 'text/csv',
    }
  if file_ext == 'tsv':
    return {
      'sep':      '\t',
      'mimetype': 'text/tab-separated-values',
    }

  # If none matched, return None
  return None


def get_delimiter_from_filepath(filepath=None, valid_file_extensions=None):
  valid_file_extensions = valid_file_extensions or {'csv'}
  if filepath:
    file_format = get_file_format(filepath[-3:], valid_formats=valid_file_extensions)
    if file_format:
      return file_format['sep']



def join_with_final(text, sep='', final=None, final_if_two=None):
  '''
    Like string join, but with finer control. See arguments for details.

    Arguments:
      text (list): list of strings to be joined
      sep (str): The default separator between elements.
      final (str): The separator between the penultimate and final elements.
      final_if_two (str): A special separator to use if there are exactly two elements.
  '''
  if len(text) == 2 and final_if_two is not None:
    return final_if_two.join(text)
  if final:
    return final.join([ x for x in [sep.join(text[:-1]), *text[-1:]] if x ])
  return sep.join(text)


def join_commas_and(text, truncate=None):
  '''
    Join a list like written English, using commas and "and".
    Supports list truncation, e.g. "x, y, z, and 3 more"

    Cases:
      - If there is one element, returns that element as-is
      - If there are 2 elements, returns "x and y"
      - If there are 3+ elements, returns e.g. "x, y, and z"

    Arguments:
      text (list): List of strings to be joined
      truncate (int, optional): The maximum number of elements to spell out in the list.
          If there are more elements, these are replaced with "and n more"
  '''
  if truncate:
    text = text[:truncate] + ([f'{len(text) - truncate} more'] if len(text) > truncate else [])
  return join_with_final(text, sep=', ', final=', and ', final_if_two=' and ')



def batch_generator(g, batch_size=DEFAULT_BATCH_SIZE):
  '''
    Split a generator into a generator of generators, which produce the same sequence when taken together.
    Useful for managing RAM when bulk inserting mappings into a table.
  '''
  def _inner(top):
    yield top
    for i, x in enumerate(g, start=1):
      yield x
      if i % (batch_size - 1) == 0:
        return

  for top in g:
    yield _inner(top)



def dataframe_cols_to_dict(df, key_col, val_col, drop_na=True):
  key_col_name = df.columns[key_col] if isinstance(key_col, int) else df[key_col]
  val_col_name = df.columns[val_col] if isinstance(val_col, int) else df[val_col]
  d = df.set_index(key_col_name)
  if drop_na:
    d = d.dropna()
  return d.to_dict()[val_col_name]
