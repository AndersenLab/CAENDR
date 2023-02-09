from flask import (render_template,
                  Blueprint)

from config import config
from base.utils.auth import admin_required

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
  title = "CeNDR Publications Sheet"
  sheet_url = f"{GOOGLE_SHEET_PREFIX}/{CENDR_PUBLICATIONS_SHEET}"
  return render_template('admin/google_sheet.html', **locals())
