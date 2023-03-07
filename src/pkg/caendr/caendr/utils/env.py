import os

from caendr.models.error import EnvVarError


def get_env_var(key, value=None, can_be_none=False):
  '''
    Gets an environment variable with an optional backup value.
    If value is None (env var is undefined), raises an EnvVarError with the name of the missing variable.
  '''
  v = os.environ.get(key, value)
  if v is None and not can_be_none:
    raise EnvVarError(key)
  return v


def remove_env_escape_chars(val: str):
  return val.replace('\\', '')


def convert_env_bool(val: str):
  if val and val.lower() == 'true':
    return True
  return False
