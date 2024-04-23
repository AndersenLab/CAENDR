from flask import render_template, Blueprint, abort

from config import config
from base.forms      import AnnouncementForm
from base.utils.auth import admin_required

from caendr.models.datastore      import Announcement
from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.sheets import GOOGLE_SHEET_PREFIX

ANDERSEN_LAB_STRAIN_SHEET = get_secret('ANDERSEN_LAB_STRAIN_SHEET')
CENDR_PUBLICATIONS_SHEET = get_secret('CENDR_PUBLICATIONS_SHEET')

admin_bp = Blueprint('admin',
                      __name__,
                      template_folder='templates')


@admin_bp.route('/')
@admin_required()
def admin():
  VARS = {"title": "Admin"}
  return render_template('admin/admin.html', **VARS)


@admin_bp.route('/strain_sheet')
@admin_required()
def admin_strain_sheet():
  title = "Andersen Lab Strain Sheet"
  sheet_url = f"{GOOGLE_SHEET_PREFIX}/{ANDERSEN_LAB_STRAIN_SHEET}"
  return render_template('admin/google_sheet.html', **locals())


@admin_bp.route('/publications')
@admin_required()
def admin_publications_sheet():
  title = "CaeNDR Publications Sheet"
  sheet_url = f"{GOOGLE_SHEET_PREFIX}/{CENDR_PUBLICATIONS_SHEET}"
  return render_template('admin/google_sheet.html', **locals())


@admin_bp.route('/announcements', methods=['GET'])
@admin_required()
def announcements():
  '''
    Manage the site announcements.
  '''
  return render_template('admin/announcements/list.html', **{
    'title': 'Site Announcements',
    'form':  AnnouncementForm(),
  })


@admin_bp.route('/announcements/create',                  methods=['GET'])
@admin_bp.route('/announcements/edit/<string:entity_id>', methods=['GET'])
@admin_required()
def announcements_edit(entity_id=None):
  '''
    Manage the site announcements.
  '''
  if entity_id:
    try:
      announcement = Announcement.get_ds(entity_id)
    except:
      abort(500)
  else:
    announcement = None

  # Initialize the form with the existing object (or None if creating new)
  form = AnnouncementForm(obj=announcement)

  return render_template('admin/announcements/edit.html', **{
    'title': ('Edit' if announcement else 'Create') + ' Announcement',
    'form':  form,

    'announcement': announcement,
  })
