import yaml
import hashlib
import uuid
import string
import pandas as pd

from collections import Counter
from caendr.services.logger import logger


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


def convert_data_table_to_tsv(data, columns):
  data = pd.DataFrame(data, columns=columns)
  data = data.to_csv(index=False, sep="\t")
  return data