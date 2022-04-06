import json
import re
import pandas as pd
import numpy as np

import io

from logzero import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.utils.auth import jwt_required, admin_required, get_current_user
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
  title = "All Indel Primer Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_all_indel_primers()
  return render_template('tools/indel_primer/list-all.html', **locals())


@indel_primer_bp.route("/pairwise_indel_finder/my-results")
@jwt_required()
def indel_primer_user_results():
  title = "My Indel Primer Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_user_indel_primers(user.name)
  return render_template('tools/indel_primer/list-user.html', **locals())



@indel_primer_bp.route("/pairwise_indel_finder/query_indels", methods=["POST"])
@jwt_required()
def pairwise_indel_finder_query():
  form = PairwiseIndelForm()
  if form.validate_on_submit():
    strain_1 = form.data['strain_1']
    strain_2 = form.data['strain_2']
    chrom = form.data['chromosome']
    start = form.data['start']
    stop = form.data['stop']
    results = query_indels_and_mark_overlaps(strain_1, strain_2, chrom, start, stop)
    return jsonify(results=results)
  return jsonify({"errors": form.errors})



@indel_primer_bp.route('/pairwise_indel_finder/submit', methods=["POST"])
@jwt_required()
def submit_indel_primer():
  user = get_current_user()
  data = request.get_json()
  data_hash = get_object_hash(data, length=32)
  
  props = {'site': data['site'],
            'strain_1': data['strain_1'],
            'strain_2': data['strain_2'],
            'size': data['size'],
            'data_hash': data_hash,
            'username': user.name}

  p = create_new_indel_primer(**props)
  return jsonify({'started': True,
                  'data_hash': data_hash,
                  'id': p.id })


# TODO: Move internals of this to a service function
@indel_primer_bp.route("/indel_primer/result/<id>")
@indel_primer_bp.route("/indel_primer/result/<id>/tsv/<filename>")
@jwt_required()
def pairwise_indel_query_results(id, filename = None):
    alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
    user = get_current_user()
    ip = get_indel_primer(id)

    if (not ip._exists) or (ip.username != user.name):
      flash('You do not have access to that report', 'danger')
      abort(401)

    data_hash = ip.data_hash

    title = "Indel Primer Results"
    data = fetch_ip_data(ip)
    result = fetch_ip_result(ip)
    ready = False

    if data is None:
        return abort(404, description="Indel primer report not found")
      
    data = json.loads(data.download_as_string().decode('utf-8'))
    logger.debug(data)
    # Get trait and set title
    title = f"Indel Primer Results {data['site']}"
    subtitle = f"{data['strain_1']} | {data['strain_2']}"

    # Set indel information
    size = data['size']
    chrom, indel_start, indel_stop = re.split(":|-", data['site'])
    indel_start, indel_stop = int(indel_start), int(indel_stop)

    if result:
        result = result.download_as_string().decode('utf-8')
        result = pd.read_csv(io.StringIO(result), sep="\t")

        # Check for no results
        empty = True if len(result) == 0 else False
        ready = True
        ip.status = 'COMPLETE'
        ip.empty = empty
        ip.save()
        if empty is False:
            # left primer
            result['left_primer_start'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[0]).astype(int)
            result['left_primer_stop'] = result.apply(lambda x: len(x['primer_left']) + x['left_primer_start'], axis=1)

            # right primer
            result['right_primer_stop'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[1]).astype(int)
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
            result.amp_stop = result.amp_stop.astype(int)

            result["N"] = np.arange(len(result)) + 1
            # Setup output table
            format_table = result[["N",
                                "CHROM",
                                "primer_left",
                                "left_primer_start",
                                "left_primer_stop",
                                "left_melting_temp",
                                "primer_right",
                                "right_primer_start",
                                "right_primer_stop",
                                "right_melting_temp",
                                "REF_product_size",
                                "ALT_product_size"]]

            # Format table column names
            COLUMN_NAMES = ["Primer Set",
                            "Chrom",
                            "Left Primer (LP)",
                            "LP Start",
                            "LP Stop",
                            "LP Melting Temp",
                            "Right Primer (RP)",
                            "RP Start",
                            "RP Stop",
                            "RP Melting Temp",
                            f"{ref_strain} (REF) amplicon size",
                            f"{alt_strain} (ALT) amplicon size"]

            format_table.columns = COLUMN_NAMES

            records = result.to_dict('records')

    if request.path.endswith("tsv"):
        # Return TSV of results
        return Response(format_table.to_csv(sep="\t"), mimetype="text/tab-separated-values")

    return render_template("tools/indel_primer/view.html", **locals())


