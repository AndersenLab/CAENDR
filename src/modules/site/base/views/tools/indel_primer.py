import json
import re
import pandas as pd
import numpy as np

import io

from logzero import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.utils.auth import jwt_required, admin_required, get_current_user, user_is_admin
from base.forms import PairwiseIndelForm

from caendr.services.dataset_release import get_browser_tracks_path
from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.data import get_object_hash

from caendr.services.indel_primer import get_sv_strains, query_indels_and_mark_overlaps, create_new_indel_primer, get_indel_primer, fetch_ip_data, fetch_ip_result, get_all_indel_primers, get_user_indel_primers



# Tools blueprint
indel_primer_bp = Blueprint('indel_primer',
                            __name__,
                            template_folder='tools')

from caendr.utils.constants import CHROM_NUMERIC

@indel_primer_bp.route('/pairwise_indel_finder', methods=['GET'])
@jwt_required()
def indel_primer():
  form = PairwiseIndelForm(request.form)
  title = "Pairwise Indel Finder"
  strains = get_sv_strains()
  chroms = CHROM_NUMERIC.keys()
  fluid_container = True
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  
  # TODO: REPLACE THESE STATIC VALUES
  divergent_track_summary_url = "//storage.googleapis.com/elegansvariation.org/browser_tracks/lee2020.divergent_regions_all.bed.gz"
  fasta_url = "//storage.googleapis.com/elegansvariation.org/browser_tracks/c_elegans.PRJNA13758.WS276.genomic.fa"
  
  return render_template('tools/indel_primer/submit.html', **locals())



@indel_primer_bp.route("/pairwise_indel_finder/all-results")
@admin_required()
def indel_primer_all_results():
  return render_template('tools/indel_primer/list-all.html', **{

    # Page info
    'title': "All Indel Primer Results",
    'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

    # User info
    'user':  get_current_user(),
    'items': get_all_indel_primers(),
  })



@indel_primer_bp.route("/pairwise_indel_finder/my-results")
@jwt_required()
def indel_primer_user_results():

  # Get user
  user = get_current_user()

  return render_template('tools/indel_primer/list-user.html', **{

    # Page info
    'title': 'My Indel Primer Results',
    'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools'), },

    # User info
    'user':  user,
    'items': get_user_indel_primers(user.name),
  })



@indel_primer_bp.route("/pairwise_indel_finder/query_indels", methods=["POST"])
@jwt_required()
def pairwise_indel_finder_query():

  # Validate query form
  form = PairwiseIndelForm()
  if form.validate_on_submit():

    # Extract fields
    strain_1 = form.data['strain_1']
    strain_2 = form.data['strain_2']
    chrom    = form.data['chromosome']
    start    = form.data['start']
    stop     = form.data['stop']

    # Run query and return results
    results = query_indels_and_mark_overlaps(strain_1, strain_2, chrom, start, stop)
    return jsonify({ 'results': results })

  # If form not valid, return errors
  return jsonify({ 'errors': form.errors })



@indel_primer_bp.route('/pairwise_indel_finder/submit', methods=["POST"])
@jwt_required()
def submit_indel_primer():

  # Get current user
  user = get_current_user()

  # Get info about data
  data      = request.get_json()
  data_hash = get_object_hash(data, length=32)

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Create new Indel Primer
  p = create_new_indel_primer(**{
    'site':      data['site'],
    'strain_1':  data['strain_1'],
    'strain_2':  data['strain_2'],
    'size':      data['size'],
    'data_hash': data_hash,
    'username':  user.name,
    'no_cache':  no_cache,
  })

  # Notify user that task has been started
  return jsonify({
    'started':   True,
    'data_hash': data_hash,
    'id':        p.id,
  })


# TODO: Move internals of this to a service function
@indel_primer_bp.route("/indel_primer/result/<id>")
@indel_primer_bp.route("/indel_primer/result/<id>/tsv/<filename>")
@jwt_required()
def pairwise_indel_query_results(id, filename = None):

    # Get user and primer result
    user = get_current_user()
    ip = get_indel_primer(id)

    # Check that user can view this report
    # TODO: Should admin users be able to view reports with different filenames?
    if (not ip._exists) or (ip.username != user.name):
      flash('You do not have access to that report', 'danger')
      abort(401)

    # Fetch job data (parameters of original query) and results
    data   = fetch_ip_data(ip)
    result = fetch_ip_result(ip)
    ready  = False

    # If no indel primer submission exists, return 404
    if data is None:
        return abort(404, description="Indel primer report not found")

    # Parse submission data into JSON object
    data = json.loads(data.download_as_string().decode('utf-8'))
    logger.debug(data)

    # Set indel information
    chrom, indel_start, indel_stop = re.split(":|-", data['site'])
    indel_start, indel_stop = int(indel_start), int(indel_stop)

    # Initialize vars with default values
    format_table = None
    empty        = False

    # If result file exists, display
    if result:
        ready = True

        # Download results file as string
        result = result.download_as_string().decode('utf-8')

        # Check for empty results file
        if len(result) == 0:
          empty = True
          # ip.status = 'ERROR'

        # Separate results by tabs, and check for empty data frame (headers exist but no data)
        else:
          result = pd.read_csv(io.StringIO(result), sep="\t")
          empty  = result.empty

        # Update indel primer entity
        if ip.status != 'ERROR':
          ip.status = 'COMPLETE'
        ip.empty  = empty
        ip.save()

        # If results file has data, parse
        if not empty:

            # Left primer
            result['left_primer_start'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[0]).astype(int)
            result['left_primer_stop']  = result.apply(lambda x: len(x['primer_left']) + x['left_primer_start'], axis=1)

            # Right primer
            result['right_primer_stop']  = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[1]).astype(int)
            result['right_primer_start'] = result.apply(lambda x:  x['right_primer_stop'] - len(x['primer_right']), axis=1)

            # Output left and right melting temperatures.
            result[["left_melting_temp", "right_melting_temp"]] = result["melting_temperature"].str.split(",", expand = True)

            # REF Strain and ALT Strain
            ref_strain = result['0/0'].unique()[0]
            alt_strain = result['1/1'].unique()[0]

            # Extract chromosome and amplicon start/stop
            result[[None, "amp_start", "amp_stop"]] = result.amplicon_region.str.split(pat=":|-", expand=True)

            # Convert types
            result.amp_start = result.amp_start.astype(int)
            result.amp_stop  = result.amp_stop.astype(int)

            result["N"] = np.arange(len(result)) + 1

            # Associate table column names with the corresponding fields in the result objects
            columns = [

              # Basic Info
              ("Primer Set", "N"),
              ("Chrom", "CHROM"),

              # Left Primer
              ("Left Primer (LP)", "primer_left"),
              ("LP Start",         "left_primer_start"),
              ("LP Stop",          "left_primer_stop"),
              ("LP Melting Temp",  "left_melting_temp"),

              # Right Primer
              ("Right Primer (RP)", "primer_right"),
              ("RP Start",          "right_primer_start"),
              ("RP Stop",           "right_primer_stop"),
              ("RP Melting Temp",   "right_melting_temp"),

              # Amplicon
              (f"{ref_strain} (REF) amplicon size", "REF_product_size"),
              (f"{alt_strain} (ALT) amplicon size", "ALT_product_size"),
            ]

            # Convert list of (name, field) tuples to list of names and list of fields
            column_names, column_fields = zip(*columns)

            # Create table from results & columns
            format_table = result[list(column_fields)]
            format_table.columns = column_names


    # Return downloadable TSV of results
    if request.path.endswith("tsv"):
        return Response(format_table.to_csv(sep="\t"), mimetype="text/tab-separated-values")

    # Otherwise, return view page
    return render_template("tools/indel_primer/view.html", **{

      # Page info
      'title':    f"Indel Primer Results {data['site']}",
      'subtitle': f"{data['strain_1']} | {data['strain_2']}",
      'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

      # GCP data info
      'data_hash': ip.data_hash,
      'id': id,

      # Data
      'data':  data,
      'empty': empty,
      'ready': ready,
      'indel_start': indel_start,
      'indel_stop':  indel_stop,
      # 'size': data['size'],

      # Results
      'result': result,
      'records': result.to_dict('records') if (result is not None) else None,
      'format_table': format_table,
    })


