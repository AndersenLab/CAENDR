from flask import Blueprint, render_template, url_for, request, redirect

from base.utils.auth import admin_required, get_jwt, get_jwt_identity
from base.forms import AdminGeneBrowserTracksForm

from caendr.services.gene_browser_tracks import get_all_gene_browser_tracks, create_new_gene_browser_track

admin_gene_browser_tracks_bp = Blueprint('admin_gene_browser_tracks',
                            __name__)


@admin_gene_browser_tracks_bp.route('', methods=["GET"])
@admin_required()
def admin_gene_browser_tracks():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'Gene Browser Track Versions'
  gene_browser_track_versions = get_all_gene_browser_tracks(placeholder=False)
  return render_template('admin/browser_tracks/list.html', **locals())


@admin_gene_browser_tracks_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def create_gene_browser_tracks():
  title = 'Create Gene Browser Tracks for a Wormbase Release'
  alt_parent_breadcrumb = {"title": "Admin/Gene Browser Tracks", "url": url_for('admin_gene_browser_tracks.admin_gene_browser_tracks')}

  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminGeneBrowserTracksForm(request.form)
  if request.method == 'POST' and form.validate_on_submit():
    wormbase_version = 'WS' + request.form.get('wormbase_version')
    note = request.form.get('note')
    username = get_jwt_identity()
    
    create_new_gene_browser_track(wormbase_version, username, note=note)
    return redirect(url_for("admin_gene_browser_tracks.admin_gene_browser_tracks"), code=302)

    
  return render_template('admin/browser_tracks/create.html', **locals())