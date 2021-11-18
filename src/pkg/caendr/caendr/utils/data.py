import yaml
import json
import decimal
import os
import hashlib
import uuid
import urllib.request as request
import shutil

from contextlib import closing

from collections import Counter
from datetime import datetime
from logzero import logger
from caendr.models.error import APIBadRequestError

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

# TODO: potentially removable
def load_yaml(yaml_file):
  return yaml.load(open(f"base/static/yaml/{yaml_file}", 'r'))

def extract_json_payload(request):
  '''
    Loads the JSON payload from the body of a request
    Throws an error if unable to parse
  '''
  try:
    payload = json.loads(request.data)
    return payload
  except:
    raise APIBadRequestError("Unable to parse JSON")
    

def get_json_from_class(obj):
  """
    Iterates recursively through a class and returns json for all properties that are not set to 'None'
  """
  return json.loads(
    json.dumps(obj, default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),
              indent=4,
              allow_nan=False)
  )

class json_encoder(json.JSONEncoder):
  ''' JSON encoder class '''
  def default(self, o):
    if hasattr(o, "to_json"):
      return o.to_json()
    if hasattr(o, "__dict__"):
      return {k: v for k, v in o.__dict__.items() if k != "id" and not k.startswith("_")}
    if type(o) == decimal.Decimal:
      return float(o)
    elif isinstance(o, datetime.date):
      return str(o.isoformat())
    try:
      iterable = iter(o)
      return tuple(iterable)
    except TypeError:
      pass
    return json.JSONEncoder.default(self, o)


def dump_json(data):
  return json.dumps(data, cls=json_encoder)


def get_dir_list_sorted(path):
  """ returns a sorted list of the directory contents at the os path argument  """
  return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


def get_object_hash(object, length=10):
  ''' Generates the sha1 hash of an object encoded as a string and returns the first 'length' characters '''
  logger.debug(object)
  return hashlib.sha1(str(object).encode('utf-8')).hexdigest()[0:length]


def get_file_hash(filename, length=10):
  ''' Generates the sha1 hash of a file's contents and returns the first 'length' characters '''
  logger.debug(filename)
  BLOCKSIZE = 65536
  hasher = hashlib.sha1()
  with open(filename, 'rb') as afile:
    buf = afile.read(BLOCKSIZE)
    while len(buf) > 0:
      hasher.update(buf)
      buf = afile.read(BLOCKSIZE)
  
  return hasher.hexdigest()[0:length]


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


def download_file(url: str, fname: str):
  '''
    download_file [Downloads a file as a stream to minimize resources]
      Args:
        url (str): [URL of the file to be downloaded]
        fname (str): [The local filename given to the downloaded file]
      Returns:
        (str): [The local filename given to the downloaded file]
  '''  
  with closing(request.urlopen(url)) as r:
    with open(fname, 'wb') as f:
      shutil.copyfileobj(r, f)

  return fname


def remove_env_escape_chars(val: str):
  return val.replace('\\', '')