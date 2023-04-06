import os
from dotenv import load_dotenv
from string import Template

from caendr.services.logger import logger


# Flag to track whether the environment has been loaded
env_loaded = False


def load_env(dotenv_file='.env'):
  '''
    Loads environment variables from the given file.
  '''
  global env_loaded
  from caendr.models.error import EnvLoadError

  # Log a warning if the environment has already been loaded
  if env_loaded:
    logger.warn(f'Environment has already been loaded. Loading again from {dotenv_file}.')

  # Try to load the environment file
  try:
    load_dotenv(dotenv_file)
    env_loaded = True

  # If load fails, propagate the original error wrapped in an EnvLoadError
  except Exception as ex:
    raise EnvLoadError(dotenv_file, source=ex)



def get_env_var(key, value=None, can_be_none=False, as_template=False):
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

  # Convert variable to a template string, if desired
  if as_template:
    return Template(v.replace('{', '${'))

  # Return the value
  return v


def remove_env_escape_chars(val: str):
  return val.replace('\\', '')


def convert_env_bool(val: str):
  if val and val.lower() == 'true':
    return True
  return False



def replace_species_tokens(s, species='$SPECIES', prj='$PRJ', wb='$WB', sva='$SVA', release='$RELEASE', strain='$STRAIN'):

  # Get first argument as a string template
  if isinstance(s, str):
    t = Template(s)
  elif isinstance(s, Template):
    t = s
  else:
    raise ValueError(f'Cannot replace tokens in non-string value {s}')

  # Perform substitutions
  return t.substitute({
    'SPECIES': species,
    'RELEASE': release,
    'WB':      wb,
    'SVA':     sva,
    'PRJ':     prj,
    'STRAIN':  strain,
  })


# def replace_tokens_recursive(obj, **kwargs):
#   if isinstance(obj, str):
#     return replace_species_tokens(obj, **kwargs)
#   elif isinstance(obj, dict):
#     return { key: replace_tokens_recursive(val, **kwargs) for key, val in obj.items() }
#   else:
#     return obj