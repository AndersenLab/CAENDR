from caendr.models.error import APIUnprocessableEntity
from caendr.models.pub_sub import PubSubStatus, PubSubMessage, PubSubAttributes



def get_attribute(payload, key, can_be_none=False):
  '''
    Extract an attribute from a Pub/Sub payload.
  '''

  # Get the list of attributes
  try:
    attributes = payload.get('message')['attributes']
  except:
    raise APIUnprocessableEntity(f'Error parsing PubSub message: could not retrieve attributes')

  # Look up to provided key in the set of attributes
  value = attributes.get(key)
  if value is None and not can_be_none:
    raise APIUnprocessableEntity(f'Error parsing PubSub message: expected attribute "{key}"')
  return value
