import json
import os
import re

from pathlib import Path
from string import Template

from caendr.models.error import EnvVarError, InternalError
from caendr.models.datastore.dataset_release import DatasetRelease
from caendr.models.datastore.gene_browser_tracks import TRACKS, TRACK_PATHS, TRACK_TEMPLATES
from caendr.models.datastore.wormbase import WormbaseVersion
from caendr.models.species import SPECIES_LIST
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
  return jsonify(TRACKS)


@gene_browser_bp.route('/gbrowser/templates', methods=['GET'])
def get_track_templates():
  '''
  Get the list of browser track templates for strains.
  Returns templates as JSON strings, so every instantiation of the template is a new copy.
  '''
  return jsonify({
    key: json.dumps(template)
      for key, template in TRACK_TEMPLATES.items()
  })


@gene_browser_bp.route('/gbrowser/templates/<template>',          methods=['GET'])
@gene_browser_bp.route('/gbrowser/templates/<template>/<strain>', methods=['GET'])
def get_track_template(template = '', strain = None):
  '''
  Get a specific browser track template, potentially filled in with a given strain.
  '''

  # If no specific strain requested, send back the template as-is
  if strain is None:
    return jsonify(TRACK_TEMPLATES[template])

  # Otherwise, replace the strain name in the template before returning
  else:
    return jsonify(replace_tokens_recursive(TRACK_TEMPLATES[template], strain=strain))



@gene_browser_bp.route('/gbrowser/tracks/<species>', methods=['GET'])
def get_species_tracks(species=None):
  '''
  Get the list of default tracks and the list of strains for the given species.

  These together determine what tracks can be generated for the species.
  '''

  # Confirm that species string is valid
  if (species not in SPECIES_LIST):
    raise InternalError()

  # Get strain and isotype for all strains of given species
  strain_list = [
    {
      'strain':  strain.strain,
      'isotype': strain.isotype,
    }
    for strain in get_isotypes( species=species )
  ]

  # Send back in JSON format
  return jsonify({
    'strain_list':    strain_list,
    'species_tracks': SPECIES_LIST[species].browser_tracks,
  })



@gene_browser_bp.route('/gbrowser')
@gene_browser_bp.route('/gbrowser/')
@gene_browser_bp.route('/gbrowser/<release_version>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>/<query>')
@cache.memoize(60*60)
def gbrowser(release_version=None, region="III:11746923-11750250", query=None):
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
    'default_tracks': TRACKS,

    # Data locations
    'site_prefix':    TRACK_PATHS['site_prefix'],
    'release_path':   TRACK_PATHS['release_path'],
    'bam_bai_path':   TRACK_PATHS['bam_bai_path'],
    'fasta_filename': TRACK_PATHS['fasta_filename'],

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      '$WB':      'wb_ver',
      '$RELEASE': 'latest_release',
      '$PRJ':     'project_num',
    },

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],

    # Misc
    'fluid_container': True,
  }
  return render_template('data/gbrowser.html', **VARS)
