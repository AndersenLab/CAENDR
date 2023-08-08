from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.services.logger import logger

from caendr.models.error import APIUnprocessableEntity
from caendr.models.pub_sub import PubSubStatus, PubSubMessage, PubSubAttributes
from caendr.utils.env import get_env_var



GOOGLE_CLOUD_PROJECT_ID = get_env_var('GOOGLE_CLOUD_PROJECT_ID')

# Create the Pub/Sub service
SERVICE = discovery.build('pubsub', 'v1', credentials=GoogleCredentials.get_application_default())
parent = f'projects/{GOOGLE_CLOUD_PROJECT_ID}'


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


def publish_message(topic, data=None, **kwargs):
  '''
    Publish a message to the specified topic.
    Arbitrary keyword args are interpreted as message attributes.

    Args:
      - topic (str): The name of the topic to publish to. Omit the project name.
      - data (Optional): The message data field. If empty, at least one attribute must be provided.
      - keyword args: Attributes for this message.

    Returns:
      The ID of the published message. Unique within the topic.
  '''

  # Create and execute the request
  response = SERVICE.projects().topics().publish(topic=f'{parent}/topics/{topic}', body={
    'messages': [{
      'attributes': kwargs,
      'data': data,
    }],
  }).execute()

  # Return the message ID if possible, otherwise return None
  try:
    return response['messageIds'][0]
  except Exception as ex:
    logger.warn(f'Couldn\'t extract message ID from Pub/Sub response: {response}. Error: {ex}')
    return None
