from caendr.models.pub_sub import PubSubStatus, PubSubMessage, PubSubAttributes

def get_operation(payload):
  try:
    message = payload.get('message')
    attributes = message.get('attributes')
    operation_id = attributes.get('operation')  
    return operation_id
  except:
    return None

