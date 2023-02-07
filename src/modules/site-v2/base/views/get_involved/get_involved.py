from flask import Blueprint, render_template, url_for, request, redirect
from datetime import datetime, timezone
from caendr.services.logger import logger

from config import config

from extensions import cache

from base.forms import DonationForm
from base.utils.auth import jwt_required, get_current_user

from caendr.api.isotype import get_isotypes
from caendr.services.cloud.sheets import add_to_order_ws
from caendr.services.email import send_email, DONATION_SUBMISSION_EMAIL_TEMPLATE
from caendr.utils.data import get_object_hash


get_involved_bp = Blueprint(
  'get_involved', __name__, template_folder='templates'
)


@get_involved_bp.route('/citizen-scientists')
@cache.memoize(60*60)
def citizen_scientists():
  title = "Citizen Scientists"
  disable_parent_breadcrumb = True
  
  # TODO: REPLACE THESE TEMPORARY ASSIGNMENTs
  protocol_url = 'https://storage.googleapis.com/elegansvariation.org/static/protocols/SamplingIsolationC.elegansNaturalHabitat.pdf'
  nematode_isolation_kit_form_url = 'http://docs.google.com/forms/d/15JXAQptqCSenZMyqHHOKQH1wJe7m0n8_Q0nHMe0eTUY/viewform?formkey=dERCQ1lsamU1ZFNtOGJJUkJqVzZOOVE6MQ#gid=0'
  
  return render_template('get_involved/citizen-scientists.html', **locals())


@get_involved_bp.route('/donate', methods=['GET', 'POST'])
@jwt_required(optional=True)
def donate():
  ''' Process donation form page '''
  title = "Donate"
  disable_parent_breadcrumb = True
  form = DonationForm(request.form)

  # Autofill email
  user = get_current_user()
  if user and hasattr(user, 'email') and not form.email.data:
    form.email.data = user.email

  if form.validate_on_submit():
    # order_number is generated as a unique string
    order_obj = {
      "is_donation": True,
      "date": datetime.now(timezone.utc)
    }
    order_obj['items'] = u"{}:{}".format("CaeNDR strain and data support", form.data.get('total'))
    order_obj.update(form.data)
    order_obj['invoice_hash'] = get_object_hash(order_obj, length=8)
    order_obj['url'] = url_for('order.order_confirmation', invoice_hash=order_obj['invoice_hash'], _external=True)
    send_email({
      "from": "no-reply@elegansvariation.org",
      "to": [order_obj["email"]],
      "cc": config.get("CC_EMAILS"),
      "subject": f"CaeNDR Donation #{order_obj['invoice_hash']}",
      "text": DONATION_SUBMISSION_EMAIL_TEMPLATE.format(order_confirmation_link=order_obj.get('url'), donation_amount=order_obj.get('total'))
    })
    add_to_order_ws(order_obj)
    return redirect(url_for("order.order_confirmation", invoice_hash=order_obj["invoice_hash"]), code=302)
  return render_template('get_involved/donate.html', **locals())
