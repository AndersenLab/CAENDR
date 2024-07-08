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
from base.utils.view_decorators import parse_entity_id, validate_form
from base.forms import AdminEditBrowserTrackForm

from caendr.models.datastore import BrowserTrackDefault, BrowserTrackTemplate, Species, DatasetRelease
from caendr.models.error import NotFoundError, NonUniqueEntity
from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.data import get_file_format
from caendr.utils.json import jsonify_request

from constants import GENOME_BROWSER_TOOLS



api_tracks_bp = Blueprint(
  'api_tracks', __name__
)



#
# Main Endpoint
#


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



#
# Alternate Query Endpoint(s)
#


@api_tracks_bp.route('/datatables', methods=['GET', 'POST'])
@admin_required()
def query_datatables():

  releases = sorted(
    [
      DatasetRelease.from_name( species['release_latest'], name ) for (name, species) in Species.all().items()
    ],
    key=lambda release: release['species']['order'],
  )

  return {
    'data': [
      {
        **track.serialize(include_meta=True, include_name=True),
        'available_releases': [
          {
            'release':   release.name,
            'species':   release['species'].short_name,
            'available': track.available_in_release(release),
          } for release in releases
        ]
      }
      for track in BrowserTrackDefault.query_ds()
    ],
  }



#
# Individual Tracks
#


@api_tracks_bp.route('/track/<string:entity_id>', methods=['GET'])
@jwt_required()
@parse_entity_id(BrowserTrackDefault, required=False, kw_name_entity='track')
@jsonify_request
def view_track(track: BrowserTrackDefault = None):
  '''
    CRUD methods for a single browser track object that do NOT require admin permissions.
    Note that a JWT is required, i.e. users must be logged in.

    Methods:
      GET:    Get the data for the given browser track ID.
  '''

  # GET Request
  # Return the requested browser track
  if request.method == 'GET':
    return track.serialize()

  # If somehow the method didn't match any of the above,
  # return a Method Not Allowed error
  abort(405)


@api_tracks_bp.route('/track',                    methods=['POST'])
@api_tracks_bp.route('/track/<string:entity_id>', methods=['PATCH', 'DELETE'])
@admin_required()
@parse_entity_id(BrowserTrackDefault, required=False, kw_name_entity='track')
@validate_form(AdminEditBrowserTrackForm, methods=['POST', 'PATCH'])
@jsonify_request
def edit_track(track: BrowserTrackDefault = None, form_data = None, no_cache: bool = False):
  '''
    CRUD methods for a single browser track object that require admin permissions.

    Methods:
      POST:   Create a new browser track.
      PATCH:  Update an existing browser track.
      DELETE: Delete an existing browser track.
  '''

  # POST Request
  # Create a new browser track, and return its unique ID
  if request.method == 'POST':

    # Create and save the new browser track
    new_track = BrowserTrackDefault(**{
      prop: form_data.get(prop)
        for prop in BrowserTrackDefault.get_props_set()
        if form_data.get(prop) is not None
    })
    new_track.save()

    # Try explicitly placing the new track at the bottom of the list
    # If this fails, it will get a default order value, so we can ignore errors
    try:
      new_track['order'] = len(BrowserTrackDefault.query_ds())
      new_track.save()
    except Exception as ex:
      pass

    # Return the ID of the new browser track
    return { 'id': new_track.name }

  # PATCH Request
  # Lookup the desired announcement and update its properties
  if request.method == 'PATCH':

    # Extract the new property values from the form, casting "checked" to a bool if necessary
    new_values = {
      prop: form_data.get(prop)
        for prop in BrowserTrackDefault.get_props_set()
        if form_data.get(prop) is not None
    }
    if isinstance( form_data.get('checked'), str ):
      new_values['checked'] = form_data.get('checked').lower() == 'true'

    # If either of the "modify_" bool values are set,
    # update the corresponding field, even if the form value isn't set
    # (i.e. default to an empty list rather than not changing)

    if ( form_data.get('modify_used_in_tools') ):
      new_values['used_in_tools'] = form_data.get('used_in_tools', [])

    if ( form_data.get('availablity') or form_data.get('modify_availability') ):
      availability = form_data.get('availability', [])
      # TODO: Actually update the availability

    # Update the browser track object
    track.set_properties(**new_values)
    track.save()
    return { 'id': track.name }

  # If somehow the method didn't match any of the above,
  # return a Method Not Allowed error
  abort(405)


@api_tracks_bp.route('/parameters/<string:tool_id>', methods=['GET'])
@jwt_required()
@jsonify_request
def get_track_parameters(tool_id: str):
  '''
    Get the IGV Browser parameters for all tracks used in the given tool.
  '''

  # Validate requested tool ID
  if tool_id not in (tool_id for (tool_id, tool_name) in GENOME_BROWSER_TOOLS):
    abort(404)

  # Return the IGV browser parameter objects for each track used in the requested tool
  tracks = [
    track['params']
      for track in BrowserTrackDefault.query_ds()
      if tool_id in track['used_in_tools']
  ]
  return tracks



#
# Other API Methods
#


@api_tracks_bp.route('/order', methods=["POST"])
@admin_required()
@jsonify_request
def reorder():
  '''
    Change the order of the given browser tracks.

    Expects body as mapping from browser track ID to new order.
    Any browser tracks not given in the body will not be changed.

    It is on the caller to ensure the new order is consistent, i.e. that no two tracks
    have the same order.  In this case, their order will be undefined.

    TODO: Should this function just take a list of IDs in the desired order,
          and assign the order field "implicitly"?
  '''

  # Retrieve all browser tracks in the request body, aborting if any lookup fails
  try:
    tracks = [
      (BrowserTrackDefault.get_ds(track_id, silent=False), new_order)
        for (track_id, new_order) in request.json.items()
    ]
  except NotFoundError as ex:
    abort(422, description=ex.description)
  except Exception as ex:
    abort(400)

  # Update all the orders locally
  for track, new_order in tracks:
    track['order'] = new_order

  # Save new order in one batch transaction
  # If this fails, it should all fail together
  BrowserTrackDefault.save_batch(*[track for (track, new_order) in tracks])

  # Return success
  return {}
