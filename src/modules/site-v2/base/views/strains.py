from caendr.services.logger import logger
from flask import (render_template,
                   request,
                   url_for,
                   redirect,
                   Response,
                   Blueprint,
                   abort,
                   flash,
                   Markup,
                   stream_with_context,
                   jsonify,
                   make_response)

from config import config
from extensions import cache, compress

from caendr.api.strain import get_strains, query_strains, get_strain_sets, get_strain_img_url
from caendr.models.sql import Strain
from caendr.utils.json import dump_json
from caendr.utils.data import get_file_format
from caendr.utils.env import get_env_var
from caendr.models.datastore import SPECIES_LIST
from caendr.models.datastore.cart import Cart
from caendr.models.error import NotFoundError
from caendr.services.dataset_release import get_all_dataset_releases, find_dataset_release, get_latest_dataset_release_version

"""
Author: Daniel E. Cook

These views handle strain orders

"""
import uuid
import os
from datetime import datetime, timezone
from flask import render_template, request, url_for, redirect, Blueprint, abort, flash

from config import config
from base.forms import OrderForm, StrainListForm
from base.utils.auth import jwt_required, get_current_user
from caendr.utils.env import get_env_var

from caendr.services.email import send_email, ORDER_SUBMISSION_EMAIL_TEMPLATE
from caendr.services.cloud.sheets import add_to_order_ws, lookup_order
from caendr.services.cloud.secret import get_secret

MODULE_SITE_CART_COOKIE_NAME = get_env_var('MODULE_SITE_CART_COOKIE_NAME')
MODULE_SITE_CART_COOKIE_AGE_SECONDS = get_env_var('MODULE_SITE_CART_COOKIE_AGE_SECONDS', var_type=int)
STRAIN_SUBMISSION_URL = get_env_var('MODULE_SITE_STRAIN_SUBMISSION_URL')

strains_bp = Blueprint('request_strains',
                        __name__,
                        template_folder='templates')


@strains_bp.route('/map')
@cache.memoize(60*60)
def strains_map():
  """ Redirect base route to the strain list page """
  title = 'Strain Map'
  strains = get_strains()
  strain_listing = [s.to_json() for s in strains]
  return render_template('strain/map.html', **locals())

@strains_bp.route('/isotype_list')
@cache.memoize(60*60)
def strains_list():
  """ Strain list of all wild isolates within the SQL database and a table of all strains """
  VARS = {'title': 'Isotype List',
          'strain_listing': get_strains()}
  return render_template('strain/list.html', **VARS)

@strains_bp.route('/issues')
@cache.memoize(60*60)
def strains_issues():
  """ Strain issues shows latest data releases table of strain issues """
  VARS = {'title': 'Strain Issues',
          'strain_listing_issues': get_strains(issues=True)}
  return render_template('strain/issues.html', **VARS)


@strains_bp.route('/external-links')
@cache.memoize(60*60)
def external_links():
  """ Shows external website links """
  title = 'External Links'
  return render_template('strain/external_links.html', **locals())


#
# Strain Data
#
@strains_bp.route('/download/<release_name>/<species_name>/strain-data/<file_ext>')
@cache.memoize(60*60)
def strains_data_csv(release_name, species_name, file_ext):
  """
    Dumps strain dataset; Normalizes lat/lon on the way out.
  """

  # Validate release
  try:
    if release_name == 'latest':
      release = get_latest_dataset_release_version()
    else:
      release = find_dataset_release(get_all_dataset_releases(order='-version'), release_name)
  except NotFoundError:
    abort(404)

  # Validate species
  if species_name not in SPECIES_LIST:
    abort(404)

  # Get file settings from the extension, rejecting bad extensions
  file_format = get_file_format(file_ext, valid_formats=['csv', 'tsv'])
  if file_format is None:
    abort(404)

  # Generator function to produce the file line-by-line
  def generate():
    strains_by_species = query_strains(species=species_name, issues=False)
    col_list = list(Strain.__mapper__.columns)
    col_order = [1, 0, 3, 4, 5, 7, 8, 9, 10, 28, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 2, 6]
    col_list[:] = [col_list[i] for i in col_order]
    header = [x.name for x in col_list]
    yield file_format['sep'].join(header) + "\n"
    for row in strains_by_species:
      row = [getattr(row, column.name) for column in col_list]
      yield file_format['sep'].join(map(str, row)) + "\n"

  # Stream the response as a file with the correct filename
  resp = Response(stream_with_context(generate()), mimetype=file_format['mimetype'])
  resp.headers['Content-Disposition'] = f'filename={release["version"]}_{species_name}_strain_data.{file_ext}'
  return resp


#
# Strain Catalog
#

@strains_bp.route('/', methods=['GET', 'POST'])
@cache.memoize(60*60)
def request_strains():
    flash(Markup("<strong>Please note:</strong> although the site is currently accepting orders, orders will <u>not ship</u> until Fall 2023."), category="warning")

    try:
      strain_listing = get_strains()
    except Exception:
      strain_listing = []
    try:
      strain_sets = get_strain_sets()
    except Exception:
      strain_sets = {}

    return render_template('strain/catalog.html', **{
      'title': "Strain Catalog",
      'warning': request.args.get('warning'),
      'form': StrainListForm(request.form),

      'strain_listing': strain_listing,
      'strain_sets':    strain_sets,
    })

#
# Strain Ordering Pages
#

@strains_bp.route('/checkout', methods=['POST'])
@jwt_required(optional=True)
def order_page_post():
  form = OrderForm()
  user = get_current_user()
  cart_id = request.cookies.get(MODULE_SITE_CART_COOKIE_NAME)
  if user:
    users_cart = Cart.lookup_by_user(user['email'])
  elif cart_id:
    users_cart = Cart(cart_id)
  else:
    users_cart = Cart(**{'items': []})

  if 'order_form' not in request.form:
    """ adding items to the cart """
    req = request.get_json()
    added_items = req.get('strains')
    if (len(added_items) == 0):
      flash("You must select strains/sets from the catalog", 'error')
      return redirect(url_for("request_strains.request_strains"))
 
    for item in added_items:
      users_cart.add_item(item)

    users_cart.update_version()
    users_cart.save()

    resp = make_response(jsonify({'status': 'OK'}))
    if not user:
      resp.set_cookie(MODULE_SITE_CART_COOKIE_NAME, users_cart.name, max_age=MODULE_SITE_CART_COOKIE_AGE_SECONDS)
    
    return resp
    
  else:
    if not form.validate_on_submit():
      # handle form validation errors
      title = "Order Summary"
      cartItems = users_cart['items'] 
      for item in cartItems:
        item_price = Cart.get_price(item)
        item['price'] = item_price
      totalPrice = sum(item['price'] for item in cartItems)
      return render_template('order/order.html', **locals())
    else:
        """ submitting the order """
        cartItems = users_cart['items']
         # check the version
        if int(users_cart['version']) != int(form.version.data) or len(cartItems) == 0:
          flash("There was a problem with your order, please try again.", 'warning')
          return redirect(url_for('request_strains.order_page_index'))
        
        if form.shipping_service.data == 'Flat Rate Shipping':
          cartItems.append({'name': 'Flat Rate Shipping'})
        for item in cartItems:
          item_price = Cart.get_price(item)
          item['price'] = item_price
        totalPrice = sum(item['price'] for item in cartItems)

        # When the user confirms their order it is processed below.
        order_obj = {'total': totalPrice,
                      'date': datetime.now(timezone.utc).date().isoformat(),
                      'is_donation': False}
        order_obj.update(form.data)
        order_obj['phone'] = order_obj['phone'].strip("+")
        order_obj['items'] = '\n'.join(sorted([f"{item['name']}:{item['price']}" for item in cartItems]))
        order_obj['invoice_hash'] = str(uuid.uuid4()).split("-")[0]
        order_obj["order_confirmation_link"] = url_for('request_strains.order_confirmation', invoice_hash=order_obj['invoice_hash'], _external=True)
        send_email({"from": "no-reply@elegansvariation.org",
                    "to": [order_obj["email"]],
                    "cc": config.get("CC_EMAILS"),
                    "subject": "CeNDR Order #" + str(order_obj["invoice_hash"]),
                    "text": ORDER_SUBMISSION_EMAIL_TEMPLATE.format(**order_obj)})

        # Save to google sheet
        add_to_order_ws(order_obj)

        # Mark the cart is deleted
        users_cart.soft_delete()
        users_cart.save()

        flash("Thank you for submitting your order! Please follow the instructions below to complete your order.", 'success')
        resp = make_response(redirect(url_for("request_strains.order_confirmation", invoice_hash=order_obj['invoice_hash']), code=302))

        # delete cartID from cookies
        if cart_id is not None:
          resp.delete_cookie(MODULE_SITE_CART_COOKIE_NAME)          
        return resp      


@strains_bp.route('/checkout', methods=['PUT'])
@jwt_required(optional=True)
def order_page_remove():
  """ This view handles removing items from the cart """
  form = OrderForm()
  user = get_current_user()
  cart_id = request.cookies.get(MODULE_SITE_CART_COOKIE_NAME)
  req = request.get_json()
  item_to_remove = req.get('itemToRemove')

  if not user and not cart_id:
    return jsonify({'error': 'Cart is not found'}), 400
  elif user:
    users_cart = Cart.lookup_by_user(user['email'])
  else:
    users_cart = Cart(cart_id)

  # remove item from the cart
  users_cart.remove_item(item_to_remove)
  users_cart.update_version()

  users_cart.save()

  return jsonify({'status': 'OK'}), 200

@strains_bp.route('/checkout')
@jwt_required(optional=True)
def order_page_index():
  """ This view handles the checkout page """
  form = OrderForm()
  user = get_current_user()
  cart_id = request.cookies.get(MODULE_SITE_CART_COOKIE_NAME)

  if user and hasattr(user, 'email') and not form.email.data:
    form.email.data = user.email
  
  flash(Markup("<strong>Please note:</strong> although the site is currently able to accept orders, orders will <u>not ship</u> until Fall 2023."), category="warning")
  title = "Order Summary"

  if not user and not cart_id:
    cartItems = []
  elif user:
    users_cart = Cart.lookup_by_user(user['email'])
    cartItems = users_cart['items']  
  else:
    users_cart = Cart(cart_id)
    cartItems = users_cart['items']
  
  form.version.data = users_cart['version']

  if len(cartItems) == 0:
    return render_template('order/order.html', title=title, form=form)

  else:
    for item in cartItems:
      item['price'] = Cart.get_price(item)
    totalPrice = sum(item['price'] for item in cartItems)

    
    return render_template('order/order.html', title=title, cartItems=cartItems, totalPrice=totalPrice, form=form)
  

@strains_bp.route("/checkout/confirmation/<invoice_hash>", methods=['GET', 'POST'])
def order_confirmation(invoice_hash):
  order_obj = lookup_order(invoice_hash)
  if order_obj is None:
    abort(404)
  else:
    order_obj["items"] = {x.split(":")[0]: float(x.split(":")[1])
                          for x in order_obj['items'].split("\n")}
    items = [{'strain': k, 'price': v} for k, v in order_obj["items"].items()]
    strains = get_strains()
    
    # get species
    for item in items:
      for strain in strains:
        if item['strain'] == strain.isotype:
          item['species'] = strain.species_name
          break
        else:
          item['species'] = ''

    title = "Order Confirmation"
    invoice = f"Invoice {order_obj['invoice_hash']}"
    SUPPORT_EMAIL = get_secret('SUPPORT_EMAIL')
    return render_template('order/order_confirm.html', **locals())
  
    
@strains_bp.route('/submit')
@cache.memoize(60*60)
def strains_submission_page():
  """
      Google form for submitting strains
  """
  title = "Strain Submission"
  # TODO: Move this to configurable location
  #STRAIN_SUBMISSION_FORM = '1w0VjB3jvAZmQlDbxoTx_SKkRo2uJ6TcjjX-emaQnHlQ'
  #strain_submission_url = f'https://docs.google.com/forms/d/{STRAIN_SUBMISSION_FORM}/viewform?embedded=true'
  strain_submission_url = STRAIN_SUBMISSION_URL
  return render_template('strain/submission.html', **locals())


