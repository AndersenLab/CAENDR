import json
import os
import re

from pathlib import Path
from string import Template

from caendr.models.error import EnvVarError, InternalError
from caendr.models.datastore.dataset_release import DatasetRelease
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

def is_valid_wormbase_version(value = None):
  if value is None:
    return False
  regex = r"^ws[0-9]+$"
  return re.match(regex, value, flags=re.IGNORECASE) is not None

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

  # Initialize trackset with non-templated tracks
  trackset = { key: val for key, val in TRACKS['tracks'].items() }

  # Generate tracks for each strain by filling out templates
  trackset.update({
    replace_tokens(template_name, strain=strain.strain): replace_tokens_recursive(template, strain=strain.strain)
      for template_name, template in TRACKS['templates'].items()
      for strain in get_isotypes()
  })

  # Send back in JSON format
  return jsonify(trackset)



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

  wormbase_version_override = request.args.get('wormbase_version', None)
  if (wormbase_version_override is not None) and is_valid_wormbase_version(wormbase_version_override):
    wormbase_version = wormbase_version_override.upper()
  else:
    wormbase_version = dataset_release.wormbase_version    
    # OVERRIDE wormbase_version  (default to 276 until 283 IGB data is available) 
    wormbase_version = 'WS276'

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

    # Misc
    'fluid_container': True
  }
  return render_template('data/gbrowser.html', **VARS)
