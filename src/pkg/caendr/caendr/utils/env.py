import os
from dotenv import load_dotenv

from caendr.services.logger import logger


# Flag to track whether the environment has been loaded
env_loaded = False


def load_env(dotenv_file='.env'):
  '''
    Loads environment variables from the given file.
  '''
  global env_loaded
  from caendr.models.error import EnvLoadError

  # Try to load the environment file
  try:
    load_dotenv(dotenv_file)
    env_loaded = True

  # If load fails, propagate the original error wrapped in an EnvLoadError
  except Exception as ex:
    raise EnvLoadError(dotenv_file, source=ex)



def get_env_var(key, value=None, can_be_none=False):
  '''
    Gets an environment variable with an optional backup value.
    If value is None (env var is undefined), raises an EnvVarError with the name of the missing variable.
  '''
  global env_loaded
  from caendr.models.error import EnvNotLoadedError, EnvVarError

  # If environment hasn't been loaded yet, raise a warning or an error depending on whether this
  # variable can be left undefined
  if not env_loaded:
    if (value is not None) or can_be_none:
      logger.warn(f'No environment loaded: setting environment variable {key} to default value.')
      return value
    else:
      raise EnvNotLoadedError(key)

  # Get the value from the environment and return, raising an error if invalid
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
