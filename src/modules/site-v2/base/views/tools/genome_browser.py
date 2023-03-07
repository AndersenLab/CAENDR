import json
import re

from string import Template

from caendr.models.error import InternalError
from caendr.models.datastore.browser_track import BrowserTrack, BrowserTrackDefault, BrowserTrackTemplate
from caendr.models.datastore.dataset_release import DatasetRelease
from caendr.models.datastore.wormbase import WormbaseVersion
from caendr.models.datastore import SPECIES_LIST
from flask import (render_template,
                    Blueprint,
                    jsonify,
                    request,
                    url_for)
from extensions import cache

from caendr.api.isotype import get_isotypes
from caendr.services.dataset_release import get_dataset_release, get_latest_dataset_release_version


genome_browser_bp = Blueprint(
  'genome_browser', __name__, template_folder='templates'
)



# TODO: Move validators and get_dataset to new module / service

def is_valid_release_version(value = None):
  if value is None:
    return False
  return value.isdigit()

def get_dataset_release_or_latest(release_version = None):
  if release_version is None or not is_valid_release_version(release_version):
    return get_latest_dataset_release_version()
  dataset_release = get_dataset_release(release_version)
  if dataset_release is not None:
    dataset_release
  return get_latest_dataset_release_version()


def replace_tokens(s, species='$SPECIES', prj='$PRJ', wb='$WB', sva='$SVA', release='$RELEASE', strain='$STRAIN'):
  return Template(s).substitute({
    'SPECIES': species,
    'RELEASE': release,
    'WB':      wb,
    'SVA':     sva,
    'PRJ':     prj,
    'STRAIN':  strain,
  })

def replace_tokens_recursive(obj, **kwargs):
  if isinstance(obj, str):
    return replace_tokens(obj, **kwargs)
  elif isinstance(obj, dict):
    return { key: replace_tokens_recursive(val, **kwargs) for key, val in obj.items() }
  else:
    return obj



@genome_browser_bp.route('/gbrowser/tracks', methods=['GET'])
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
      track['name']: json.dumps( dict(track) )
        for track in BrowserTrackDefault.query_ds_visible()
    },
    'templates': {
      track['template_name']: json.dumps( dict(track) )
        for track in BrowserTrackTemplate.query_ds_visible()
    },
  })



@genome_browser_bp.route('/genome-browser')
@genome_browser_bp.route('/genome-browser/')
@genome_browser_bp.route('/genome-browser/<release_version>')
@genome_browser_bp.route('/genome-browser/<release_version>/<region>')
@genome_browser_bp.route('/genome-browser/<release_version>/<region>/<query>')
@cache.memoize(60*60)
def genome_browser(release_version=None, region="III:11746923-11750250", query=None):
  dataset_release = get_dataset_release_or_latest(release_version)

  # Allow WB version to be overridden w URL variable
  wormbase_version_override_str = request.args.get('wormbase_version', None)
  if WormbaseVersion.validate(wormbase_version_override_str):
    wormbase_version = WormbaseVersion(wormbase_version_override_str)

  # Default to version 276
  else:
    # wormbase_version = wormbase_version_override or dataset_release.wormbase_version
    wormbase_version = WormbaseVersion('WS276')

  # dataset_release_prefix = '//storage.googleapis.com/elegansvariation.org/releases'
  # track_url_prefix       = '//storage.googleapis.com/elegansvariation.org/browser_tracks'
  # bam_bai_url_prefix     = '//storage.googleapis.com/elegansvariation.org/bam'


  # Get strain and isotype for all strains of each species
  # Produces a dictionary from species ID to list of strains
  strain_listing = {
    species: [
      {
        'strain':  strain.strain,
        'isotype': strain.isotype,
      }
      for strain in get_isotypes( species=species )
    ]
    for species in SPECIES_LIST
  }

  # Render the page
  return render_template('tools/genome_browser/gbrowser.html', **{

    # Page info
    'title': f"Genome Browser",
    'alt_parent_breadcrumb': {
      "title": "Tools",
      "url": url_for('tools.tools')
    },

    # Data
    'region':         region,
    'query':          query,
    'strain_listing': strain_listing,
    'species_list':   SPECIES_LIST,

    # Tracks
    'default_tracks': sorted(BrowserTrackDefault.query_ds_visible(), key = lambda x: x['order'] ),

    # Data locations
    'fasta_url': BrowserTrack.get_fasta_path_full(),

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      'WB':      'wb_ver',
      'RELEASE': 'latest_release',
      'PRJ':     'project_num',
    },

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],

    # Misc
    'fluid_container': True,
  })