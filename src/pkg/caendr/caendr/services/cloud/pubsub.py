def get_operation(payload):
  try:
    message = payload.get('message')
    attributes = message.get('attributes')
    operation_id = attributes.get('operation')  
    return operation_id
  except:
    return None


class PubSubStatus(object):
  def __init__(self, message=None, subscription=None):
    self.message = message
    self.subscription = subscription

class PubSubMessage(object):
  def __init__(self, attributes=None, message_id=None, publish_time=None):
    self.attributes = attributes
    self.message_id = message_id
    self.publish_time = publish_time

class PubSubAttributes(object):
  def __init__(self, operation=None, timestamp=None):
    self.operation = operation
    self.timestamp = timestamp