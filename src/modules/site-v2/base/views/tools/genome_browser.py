import json

from caendr.models.datastore.browser_track import BrowserTrackDefault, BrowserTrackTemplate
from caendr.models.datastore import DatasetRelease, Species
from flask import ( render_template,
                    Blueprint,
                    jsonify,
                    url_for,
                    abort,
                  )
from extensions import cache
from base.forms import SpeciesSelectForm

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



@genome_browser_bp.route('/tracks', methods=['GET'])
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
      track['name']: json.dumps( track.serialize() )
        for track in BrowserTrackDefault.query_ds()
    },
    'templates': {
      track['template_name']: json.dumps( track.serialize() )
        for track in BrowserTrackTemplate.query_ds()
    },
  })



@genome_browser_bp.route('/')
@genome_browser_bp.route('/<region>')
@genome_browser_bp.route('/<region>/<query>')
@cache.memoize(60*60)
def genome_browser(region="III:11746923-11750250", query=None):

  # Special case: IGV browser looks for a file igv.css.map at its path,
  # which is picked up in the first string variable (`region`).
  # In this case, return a 404 to signify the desired file does not exist.
  if region == 'igv.css.map':
    abort(404)

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
    for species in Species.all()
  }

  # Render the page
  return render_template('tools/genome_browser/gbrowser.html', **{

    # Page info
    'title': f"Genome Browser",
    'tool_alt_parent_breadcrumb': {
      "title": "Tools",
      "url": url_for('tools.tools')
    },

    # Data
    'region':         region,
    'query':          query,
    'strain_listing': strain_listing,
    'species_list':   Species.all(),

    'form': SpeciesSelectForm(),

    # Tracks
    'default_tracks': sorted(BrowserTrackDefault.query_ds(), key = lambda x: x['order'] ),
    'supported_tracks': {
      species_name: get_dataset_release(species['release_latest'])['browser_tracks']
        for species_name, species in Species.all().items()
    },

    # Data locations
    'fasta_url': DatasetRelease.get_fasta_filepath_url_template().get_string_safe(),

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      'WB':      'wb_ver',
      'RELEASE': 'release_latest',
      'PRJ':     'project_num',
      'GENOME':  'fasta_genome',
    },

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    'latest_release_genomes': {
      species_name: get_dataset_release(species['release_latest'])['genome'] for species_name, species in Species.all().items()
    },

    # Misc
    'fluid_container': True,
  })