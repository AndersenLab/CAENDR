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
from caendr.utils.data import get_file_format, convert_data_to_download_file
from caendr.utils.env import get_env_var
from caendr.models.datastore import Species
from caendr.models.datastore import Cart
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

NO_REPLY_EMAIL = get_secret('NO_REPLY_EMAIL')


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
@strains_bp.route('/download/<species_name>/<release_name>/strain-data/<file_ext>')
@cache.memoize(60*60)
def strains_data_csv(species_name, release_name, file_ext):
  """
    Dumps strain dataset; Normalizes lat/lon on the way out.
  """

  # Get the species from the URL
  try:
    species = Species.from_name(species_name, from_url=True)
  except NotFoundError:
    return abort(404)

  # Validate release
  try:
    if release_name == 'latest':
      release = get_latest_dataset_release_version()
    else:
      release = find_dataset_release(get_all_dataset_releases(order='-version'), release_name)
  except NotFoundError:
    abort(404)

  # Get file settings from the extension, rejecting bad extensions
  file_format = get_file_format(file_ext, valid_formats=['csv', 'tsv'])
  if file_format is None:
    abort(404)

  # Get list of column names in desired order
  columns = Strain.get_column_names_ordered()

  # Get list of strains for this species as set of rows for pandas
  strains_by_species = query_strains(species=species.name, issues=False)
  data = ( [ getattr(row, column) for column in columns ] for row in strains_by_species )

  # Convert to a CSV/TSV file
  output = convert_data_to_download_file(data, columns, file_ext=file_ext)

  # Stream the response as a file with the correct filename
  resp = Response(output, mimetype=file_format['mimetype'])
  resp.headers['Content-Disposition'] = f'filename={release["version"]}_{species.name}_strain_data.{file_ext}'
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

    # TODO: Both species selectors on this page are rendered from the same form, so they have the same ID
    # Currently, the mapping sets selector has species disabled because it's the first on the page,
    # so it satisfies the ID query first.  To be safer, we should assign these different IDs.
    return render_template('strain/catalog.html', **{
      'title': "Strain Catalog",
      'disable_parent_breadcrumb': True,
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
        if int(users_cart['version']) != int(form.version.data) or len(users_cart) == 0:
          flash("There was a problem with your order, please try again.", 'warning')
          return redirect(url_for('request_strains.order_page_index'))
        
        if form.shipping_service.data == 'Flat Rate Shipping':
          users_cart.add_item({'name': 'Flat Rate Shipping', 'species': ''})
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
        order_obj['items'] = '\n'.join(sorted([f"name: {item['name']}, species: {item['species']}, price: {item['price']}" for item in cartItems]))
        order_obj['invoice_hash'] = str(uuid.uuid4()).split("-")[0]
        order_obj["order_confirmation_link"] = url_for('request_strains.order_confirmation', invoice_hash=order_obj['invoice_hash'], _external=True)
        send_email({
          "from": f'CaeNDR <{NO_REPLY_EMAIL}>',
          "to": [order_obj["email"]],
          "cc": config.get("CC_EMAILS"),
          "subject": "CaeNDR Order #" + str(order_obj["invoice_hash"]),
          "text": ORDER_SUBMISSION_EMAIL_TEMPLATE.format(**order_obj),
        })

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

  if not user and not cart_id:
    return render_template('order/order.html', **{
      'tool_alt_parent_breadcrumb': {"title": "Strain Catalog", "url": url_for('request_strains.request_strains')},
      'title': "Order Summary",
      'form': form
    })
  elif user:
    users_cart = Cart.lookup_by_user(user['email'])
  else:
    users_cart = Cart(cart_id)

  cartItems = users_cart['items']
  form.version.data = users_cart['version']

  for item in cartItems:
    item['price'] = Cart.get_price(item)
    species = item.get('species')
    item['species_short_name'] = Species.from_name(species).short_name
  totalPrice = sum(item['price'] for item in cartItems)

  return render_template('order/order.html', **{
    'tool_alt_parent_breadcrumb': {"title": "Strain Catalog", "url": url_for('request_strains.request_strains')},
    'title': "Order Summary",
    'cartItems': cartItems,
    'totalPrice': totalPrice,
    'form': form
  })
  

@strains_bp.route("/checkout/confirmation/<invoice_hash>", methods=['GET', 'POST'])
def order_confirmation(invoice_hash):

  # Look up the order
  order_obj = lookup_order(invoice_hash)
  if order_obj is None:
    abort(404)

  # Parse the individual items in the order into a list of dicts
  items = []
  for row in order_obj['items'].split("\n"):
    arr = row.split(', ')
    item_dict = {}
    for x in arr:
      k, v = x.split(': ')
      if k == 'price':
        v = float(v)
      item_dict[k] = v
    species = item_dict.get('species')
    if species == '':
      item_dict['species_short_name'] = ''
    else:
      item_dict['species_short_name'] = Species.from_name(species).short_name
    items.append(item_dict)

  return render_template('order/order_confirm.html', **({
    'title': "Order Confirmation",
    'tool_alt_parent_breadcrumb': {
      'title': 'Strain Catalog', 'url': url_for('request_strains.request_strains')
    },

    # Order info
    'invoice':   f"Invoice {order_obj['invoice_hash']}",
    'order_obj': order_obj,
    'items':     items,

    # Contact info
    'support_email': get_secret('SUPPORT_EMAIL'),
  }))
  
    
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


