import functools
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.services.logger import logger



def use_service(service_name, version, credentials=None):
  '''
    Decorator for functions which access a GCP service through the Google API Client library.

    Builds the desired service, and injects it as the first argument to the wrapped function.
    Closes the service after the function is run, regardless of return / raise value.
  '''
  def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      nonlocal service_name, version, credentials

      # Get default credentials if none are provided
      if credentials is None:
        credentials = GoogleCredentials.get_application_default()

      # Otherwise, if function provided, call it
      elif callable(credentials):
        credentials = credentials()

      # Build the desired service
      SERVICE = discovery.build(service_name, version, credentials=credentials)

      # Try running & returning from the decorated function
      try:
        return func(SERVICE, *args, **kwargs)

      # After function execution, ensure connections to the service are closed
      finally:
        try:
          SERVICE.close()
        except Exception as ex:
          logger.error(f'Failed to close service {service_name} ({version}): {ex}')

    return wrapper
  return decorator
