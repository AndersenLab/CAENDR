import json
import os
import re

from pathlib import Path
from string import Template

from caendr.models.error import EnvVarError, InternalError
from caendr.models.datastore.dataset_release import DatasetRelease
from caendr.models.datastore.wormbase import WormbaseVersion
from caendr.models.species import Species
from flask import (render_template,
                    Blueprint,
                    jsonify,
                    request,
                    url_for)
from extensions import cache

from caendr.api.isotype import get_isotypes
from caendr.services.dataset_release import get_dataset_release, get_latest_dataset_release_version


gene_browser_bp = Blueprint('gene_browser',
                        __name__,
                        template_folder='templates')


# Get path to current file
path = Path(os.path.dirname(__file__))

# Load the JSON file with the browser tracks
# with open(f"{str(path.parents[5])}/{os.environ['MODULE_GENE_BROWSER_TRACKS_JSON_PATH']}") as f:
with open(f"{str(path.parents[5])}/data/browser_tracks.json") as f:
  TRACKS = json.load(f)

# Filter out any hidden tracks
TRACKS['tracks'] = {
  key: val
    for key, val in TRACKS['tracks'].items()
    if not val.get('hidden', False)
}


# Load species list
SPECIES_LIST_FILE = os.environ['SPECIES_LIST_FILE']
if not SPECIES_LIST_FILE:
    raise EnvVarError()
SPECIES_LIST = Species.parse_json_file(SPECIES_LIST_FILE)



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



@gene_browser_bp.route('/gbrowser/tracks', methods=['GET'])
def get_tracks():
  '''
  Get the list of browser tracks.
  '''
  return jsonify(TRACKS['tracks'])


@gene_browser_bp.route('/gbrowser/templates', methods=['GET'])
def get_track_templates():
  '''
  Get the list of browser track templates for strains.
  Returns templates as JSON strings, so every instantiation of the template is a new copy.
  '''
  return jsonify({
    key: json.dumps(template)
      for key, template in TRACKS['templates'].items()
  })


@gene_browser_bp.route('/gbrowser/templates/<template>',          methods=['GET'])
@gene_browser_bp.route('/gbrowser/templates/<template>/<strain>', methods=['GET'])
def get_track_template(template = '', strain = None):
  '''
  Get a specific browser track template, potentially filled in with a given strain.
  '''

  # If no specific strain requested, send back the template as-is
  if strain is None:
    return jsonify(TRACKS['templates'][template])

  # Otherwise, replace the strain name in the template before returning
  else:
    return jsonify(replace_tokens_recursive(TRACKS['templates'][template], strain=strain))



@gene_browser_bp.route('/gbrowser/strains/<species>', methods=['GET'])
def get_strains(species=None):
  '''
  Get the list of strains for the given species.
  '''

  if species == 'c_elegans':
    result = [
      {
        'strain':  strain.strain,
        'isotype': strain.isotype,
      }
      for strain in get_isotypes()
    ]
  elif species == 'c_briggsae':
    result = [
      {
        'strain':  "BRC20069",
        'isotype': "BRC20069",
      },
      {
        'strain':  "BRC20075",
        'isotype': "BRC20075",
      },
      {
        'strain':  "BRC20102",
        'isotype': "BRC20102",
      },
    ]
  else:
    raise InternalError()

  # Send back in JSON format
  return jsonify(result)



@gene_browser_bp.route('/gbrowser')
@gene_browser_bp.route('/gbrowser/')
@gene_browser_bp.route('/gbrowser/<release_version>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>/<query>')
@cache.memoize(60*60)
def gbrowser(release_version=None, region="III:11746923-11750250", query=None):
  dataset_release = get_dataset_release_or_latest(release_version)

  # Allow WB version to be overridden w URL variable
  wormbase_version_override = WormbaseVersion( request.args.get('wormbase_version', None) )

  # Default to version 276
  # wormbase_version = wormbase_version_override or dataset_release.wormbase_version
  wormbase_version = wormbase_version_override or WormbaseVersion('WS276')

  # dataset_release_prefix = '//storage.googleapis.com/elegansvariation.org/releases'
  # track_url_prefix       = '//storage.googleapis.com/elegansvariation.org/browser_tracks'
  # bam_bai_url_prefix     = '//storage.googleapis.com/elegansvariation.org/bam'

  VARS = {
    # Page info
    'title': f"Genome Browser",
    'alt_parent_breadcrumb': {
      "title": "Data",
      "url": url_for('data.landing')
    },

    # Data
    'region':         region,
    'query':          query,
    'species_list':   SPECIES_LIST,

    # Tracks
    'default_tracks': TRACKS['tracks'],

    # Data locations
    'site_prefix':    TRACKS['paths']['site_prefix'],
    'release_path':   TRACKS['paths']['release_path'],
    'bam_bai_path':   TRACKS['paths']['bam_bai_path'],
    'fasta_filename': TRACKS['paths']['fasta_filename'],

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      '$WB':      'wormbase_version',
      '$RELEASE': 'latest_release',
      '$PRJ':     'project_number',
    },

    # Misc
    'fluid_container': True,
  }
  return render_template('data/gbrowser.html', **VARS)
