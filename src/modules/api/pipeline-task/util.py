import json

from caendr.models.error import APIBadRequestError

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
               allow_nan=False))
