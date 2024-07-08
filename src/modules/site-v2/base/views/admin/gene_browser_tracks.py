# Flask imports
from flask import Blueprint, render_template, url_for, request, redirect

# Site Module imports
from base.utils.auth import admin_required, get_jwt, get_jwt_identity
from base.utils.view_decorators import parse_entity_id
from base.forms import AdminGeneBrowserTracksForm, AdminEditBrowserTrackForm

# CaeNDR Package imports
from caendr.models.datastore import BrowserTrackDefault, DatasetRelease, Species
from caendr.services.cloud.storage import BlobURISchema

# from caendr.services.gene_browser_tracks import get_all_gene_browser_tracks, create_new_gene_browser_track



admin_gene_browser_tracks_bp = Blueprint(
  'admin_gene_browser_tracks', __name__
)



#
# Main Page
#


@admin_gene_browser_tracks_bp.route('/', methods=["GET"])
@admin_required()
def admin_gene_browser_tracks():
  '''
    Show a list of all genome browser tracks.
  '''

  return render_template('admin/browser_tracks/list.html', **{
    'title': 'Gene Browser Track Versions',
    'alt_parent_breadcrumb': {
      'title': 'Admin', 'url': url_for('admin.admin')
    },

    'form': AdminEditBrowserTrackForm(),
  })



#
# Individual Track Page(s)
#


@admin_gene_browser_tracks_bp.route('/create/',                 methods=["GET"])
@admin_gene_browser_tracks_bp.route('/edit/<string:entity_id>', methods=["GET"])
@admin_required()
@parse_entity_id(BrowserTrackDefault, required=False, kw_name_entity='track')
def edit_page(track: BrowserTrackDefault = None):
  '''
    View the create/edit form for browser track objects.
    Object modification (CRUD) is performed by the browser_tracks section of the API.
  '''

  # Initialize the form with the existing object (or None if creating new)
  form: AdminEditBrowserTrackForm = AdminEditBrowserTrackForm(obj=track)
  if track:
    releases = {
      name: DatasetRelease.from_name( species['release_latest'], name ) for (name, species) in Species.all().items()
    }
    form.availability.data = [
      name for name in Species.all() if track.available_in_release(releases[name])
    ]

  return render_template('admin/browser_tracks/edit.html', **{
    'title': ('Edit' if track else 'Create') + ' Browser Track',
    'form':  form,
    'track': track,
    'filepath': track.get_filepath_template(BlobURISchema.HTTPS).raw_string if track else '',
  })



# @admin_gene_browser_tracks_bp.route('/create-job', methods=["GET", "POST"])
@admin_gene_browser_tracks_bp.route('/create-job', methods=["GET"])
@admin_required()
def create_gene_browser_tracks():

  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminGeneBrowserTracksForm(request.form)

  # if request.method == 'POST' and form.validate_on_submit():
  #   wormbase_version = 'WS' + request.form.get('wormbase_version')
  #   note = request.form.get('note')
  #   username = get_jwt_identity()

  #   create_new_gene_browser_track(wormbase_version, username, note=note)
  #   return redirect(url_for("admin_gene_browser_tracks.admin_gene_browser_tracks"), code=302)

  return render_template('admin/browser_tracks/create.html', **{
    'title': 'Create Gene Browser Tracks for a Wormbase Release',
    'alt_parent_breadcrumb': {
      'title': 'Admin/Gene Browser Tracks', 'url': url_for('admin_gene_browser_tracks.admin_gene_browser_tracks')
    },

    'jwt_csrf_token': jwt_csrf_token,
    'form': form,
  })
