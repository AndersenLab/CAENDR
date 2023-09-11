import functools
from flask import jsonify

from caendr.services.logger import logger
from caendr.utils.env import get_env_var

from caendr.models.error import APIUnprocessableEntity
from caendr.models.pub_sub import PubSubStatus, PubSubMessage, PubSubAttributes

from .discovery import use_service



GOOGLE_CLOUD_PROJECT_ID = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
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


@use_service('pubsub', 'v1')
def publish_message(SERVICE, topic, data=None, **kwargs):
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


def make_pubsub_response(ack: bool):
  '''
    Create a response for a Pub/Sub push subscription, either acknowledging or not-acknowledging a message.

    If the message is acknowledged, Pub/Sub will stop sending messages.
    If not, Pub/Sub may retry the message after some period of time (based on the subscription configuration).

    For information on acknowledging push messages, see https://cloud.google.com/pubsub/docs/push#receive_push.

    Args:
      - ack (bool): Whether or not to acknowledge the message.

    Returns:
      - status (str): The response status string
      - code (int): The response code
  '''

  # To acknowledge a message, return an OK response
  # This tells Pub/Sub to stop sending requests
  if ack:
    return 'OK', 200

  # Otherwise, return a Continue response
  # This counts as a NACK (not acknowledged), which tells Pub/Sub to try the request again later (if applicable)
  return 'Continue', 100


def pubsub_endpoint(func):
  '''
    Decorator for view functions that are the target endpoint for a Pub/Sub push subscription.

    If view function returns a truthy value, acknowledges the message. Otherwise, nacks the message.
    If view function raises an error, that error is propagated.
  '''
  @functools.wraps(func)
  def wrapper(*args, **kwargs):

    # Run the decorated function, and convert its return value to a Pub/Sub response
    response_status, response_code = make_pubsub_response( func(*args, **kwargs) )

    # Return the Pub/Sub response as JSON
    return jsonify({ 'status': response_status }), response_code

  return wrapper
