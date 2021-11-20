import requests

from string import Template
from caendr.services.cloud.secret import get_secret
from logzero import logger


ELEVATION_API_KEY = get_secret('ELEVATION_API_KEY')
elevation_url_template = Template('https://maps.googleapis.com/maps/api/elevation/json?locations=$lat,$lon&key=$api_key')


def get_elevation(lat: float, lon: float):
  logger.info('Requesting elevation from Google Maps API: {lat} - {lon}')
  url = elevation_url_template.substitute(lat=lat, lon=lon, api_key=ELEVATION_API_KEY)
  result = requests.get(url)
  if result.ok:
    try:
      elevation = result.json()['results'][0]['elevation']
      logger.info('{lat} - {lon}: {elevation}')
      return elevation
    except KeyError:
      pass

  logger.error('Error requesting elevation data from Google Maps API')
  return None