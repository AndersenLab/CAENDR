import json
import decimal
import datetime

from functools import wraps
from flask import request, jsonify, Request

from caendr.models.error import JSONParseError


def jsonify_request(func):
  ''' API function - Checks to see if there is a request and if there is, returns JSON of result. '''
  @wraps(func)
  def jsonify_the_request(*args, **kwargs):
    ''' Wraps API functions and automatically jsonifies if its an API call '''
    if request:
      is_tsv = request.args.get('output') == 'tsv'
      if request.endpoint.endswith(func.__name__) and not is_tsv:
        return jsonify(func(*args, **kwargs))
    return func(*args, **kwargs)
  return jsonify_the_request


def extract_json_payload(request: Request):
  '''
    extract_json_payload [Loads the JSON payload from the body of a request]
      Args:
        request (Request): [An HTTP request with a JSON body]
      Raises:
        JSONParseError: [Throws error if parsing causes exception]
      Returns:
        (object): [A Python object]
  '''
  try:
    payload = json.loads(request.data)
    return payload
  except:
    raise JSONParseError("request JSON is malformed")


class json_encoder(json.JSONEncoder):
  def default(self, o: object):
    if hasattr(o, "to_json"):
      return o.to_json()
    if hasattr(o, "__dict__"):
      return {k: v for k, v in o.__dict__.items() if k != "id" and not k.startswith("_")}
    if type(o) == decimal.Decimal:
      return float(o)
    elif isinstance(o, datetime.date):
      return str(o.isoformat())
    try:
      iterable = iter(o)
      return tuple(iterable)
    except TypeError:
      pass
    return json.JSONEncoder.default(self, o)


def dump_json(data):
  return json.dumps(data, cls=json_encoder)


def get_json_from_class(obj):
  """
    Iterates recursively through a class and returns json for all properties that are not set to 'None'
  """
  return json.loads(
    json.dumps(obj, default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),
              indent=4,
              allow_nan=False)
  )
