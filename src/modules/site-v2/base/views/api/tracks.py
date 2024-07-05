import json

from caendr.services.logger import logger
from flask import (
  Blueprint,
  Response,
  abort,
  jsonify,
  request,
  url_for,
)

from base.utils.auth import jwt_required, admin_required, get_current_user, user_is_admin

from caendr.models.datastore import BrowserTrackDefault, BrowserTrackTemplate, Species
from caendr.models.error import NotFoundError, NonUniqueEntity
from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.data import get_file_format



api_tracks_bp = Blueprint(
  'api_tracks', __name__
)




@api_tracks_bp.route('/', methods=['GET'])
def get_tracks():
  '''
  Get the list of browser tracks.

  Returns two fields:
    - 'default':   The list of tracks that are not specific to any one strain
    - 'templates': The list of track templates to be filled out with strain data

  Templates are returned as JSON strings, so every instantiation of the template is a new copy.
  '''
  return jsonify({
    'default': {
      track['display_name']: json.dumps( track.serialize() )
        for track in BrowserTrackDefault.query_ds()
    },
    'templates': {
      track['template_name']: json.dumps( track.serialize() )
        for track in BrowserTrackTemplate.query_ds()
    },
  })



@api_tracks_bp.route('/divergent-regions', methods=['GET'])
@jwt_required()
def get_divergent_regions():

  # Get the Divergent Regions browser track
  try:
    divergent_track = BrowserTrackDefault.query_ds_unique('name', 'Divergent Regions', required=True)

  # If no track found, log an error message and continue raising with a more descriptive message
  except NotFoundError as ex:
    logger.error(ex.description)
    raise ex

  # If track could not be uniquely identified, log an error and continue with the first result
  # TODO: Should this raise a further error?
  except NonUniqueEntity as ex:
    logger.error('Could not uniquely identify Divergent Regions track.')
    divergent_track = ex.matches[0]

  # If a species was passed, check that the referenced track file exists for this species
  # If not, return a 404 error
  # If species invalid, ignore (since this is an optional URL variable)
  species = Species.get(request.args.get('species'), from_url=True)
  if species and not divergent_track.check_exists_for_species(species):
      abort(404)

  # Return the track parameters
  return jsonify(divergent_track['params'])
