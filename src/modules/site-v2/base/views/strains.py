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
from extensions import cache

from caendr.api.strain import get_strains, query_strains, get_strain_sets, get_strain_img_url
from caendr.models.sql import Strain
from caendr.utils.json import dump_json
from caendr.models.datastore.cart import Cart

"""
Author: Daniel E. Cook

These views handle strain orders

"""
import uuid
from datetime import datetime, timezone
from flask import render_template, request, url_for, redirect, Blueprint, abort, flash

from config import config
from base.forms import OrderForm
from base.utils.auth import jwt_required, get_current_user

from caendr.services.email import send_email, ORDER_SUBMISSION_EMAIL_TEMPLATE
from caendr.services.cloud.sheets import add_to_order_ws, lookup_order


strains_bp = Blueprint('request_strains',
                        __name__,
                        template_folder='templates')
#
# Strain List Page
#
@strains_bp.route('/')
@cache.memoize(60*60)
def request_strains():
  """ Load landing page """
  disable_parent_breadcrumb = True
  return render_template('strain/landing_page.html', **locals())

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
@strains_bp.route('/StrainData.tsv/<species>')
@cache.memoize(60*60)
def strains_data_tsv(species):
  """
      Dumps strain dataset; Normalizes lat/lon on the way out.
  """
  
  def generate():
    strains_by_species = query_strains(species=species, issues=False)
    col_list = list(Strain.__mapper__.columns)
    col_order = [1, 0, 3, 4, 5, 7, 8, 9, 10, 28, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 2, 6]
    col_list[:] = [col_list[i] for i in col_order]
    header = [x.name for x in col_list]
    yield '\t'.join(header) + "\n"
    for row in strains_by_species:
      row = [getattr(row, column.name) for column in col_list]
      yield '\t'.join(map(str, row)) + "\n"

  return Response(stream_with_context(generate()), mimetype="text/tab-separated-values")


#
# Isotype View
#
@strains_bp.route('/isotype/<isotype_name>/')
@strains_bp.route('/isotype/<isotype_name>/<release>')
@cache.memoize(60*60)
def isotype_page(isotype_name, release=None):
  """ Isotype page """
  isotype_strains = query_strains(isotype_name=isotype_name)
  if not isotype_strains:
    abort(404)

  # Fetch isotype images
  image_urls = {}
  for s in isotype_strains:
    image_urls[s.strain] = {'url': get_strain_img_url(s.strain),
                            'thumb': get_strain_img_url(s.strain, thumbnail=True)}

  logger.debug(image_urls)
  VARS = {"title": f"Isotype {isotype_name}",
          "isotype": isotype_strains,
          "isotype_name": isotype_name,
          "isotype_ref_strain": [x for x in isotype_strains if x.isotype_ref_strain][0],
          "strain_json_output": dump_json(isotype_strains),
          "image_urls": image_urls}
  return render_template('strain/isotype.html', **VARS)


#
# Strain Catalog
#

@strains_bp.route('/catalog', methods=['GET', 'POST'])
@cache.memoize(60*60)
def strains_catalog():
    flash(Markup("Strain mapping sets 9 and 10 will not be available until later this year."), category="primary")
    title = "Strain Catalog"
    warning = request.args.get('warning')
    strain_listing = get_strains()
    strain_sets = get_strain_sets()
    form = OrderForm()
    return render_template('strain/catalog.html', **locals())

#
# Strain Ordering Pages
#

@strains_bp.route('/checkout', methods=['POST'])
@jwt_required(optional=True)
def order_page_post():
  form = OrderForm()
  user = get_current_user()
  cartID = request.cookies.get('cartID')
  if user:
    users_cart = Cart.lookup_by_user(user['email'])
  elif cartID:
    users_cart = Cart(cartID)
  else:
    users_cart = Cart(**{'items': []})


  if 'order_form' in request.form:
    if form.validate_on_submit():
      # check the version
      if int(users_cart['version']) != int(form.version.data):
        flash("There was a problem with your order, please try again.", 'warning')
        return redirect(url_for('request_strains.order_page_index'))
      else:
        """ submitting the order """
        cartItems = users_cart['items']
        if form.shipping_service.data == 'Flat Rate Shipping':
          cartItems.append({'name': 'Flat Rate Shipping'})
        for item in cartItems:
          item_price = users_cart.get_price(item)
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
        users_cart.delete_cart()
        users_cart.save()

        flash("Thank you for submitting your order! Please follow the instructions below to complete your order.", 'success')

        # delete cartID from cookies
        if cartID:
          resp = make_response(redirect(url_for("request_strains.order_confirmation", invoice_hash=order_obj['invoice_hash']), code=302))
          resp.delete_cookie('cartID')
          return resp
        
        return redirect(url_for("request_strains.order_confirmation", invoice_hash=order_obj['invoice_hash']), code=302)
    else:
      # handle form validation errors
      title = "Order Summary"
      cartItems = users_cart['items'] 
      for item in cartItems:
        item_price = users_cart.get_price(item)
        item['price'] = item_price
      totalPrice = sum(item['price'] for item in cartItems)
      return render_template('order/order.html', **locals())

  
  else:
    """ adding items to the cart """
    added_items = request.get_json()['strains']
    if (len(added_items) == 0):
      flash("You must select strains/sets from the catalog", 'error')
      return redirect(url_for("request_strains.strains_catalog"))
 
    for item in added_items:
      users_cart.add_item(item)
    
    users_cart.update_version()
    users_cart.save()

    resp = make_response(jsonify({'status': 'OK'}))
    if not user:
      resp.set_cookie('cartID', users_cart.name)
    
    return resp

@strains_bp.route('/checkout', methods=['PUT'])
@jwt_required(optional=True)
def order_page_remove():
  """ This view handles removing items from the cart """
  form = OrderForm()
  user = get_current_user()
  item_to_remove = request.get_json()['itemToRemove']
  
  # get cart
  if user:
    users_cart = Cart.lookup_by_user(user['email'])
  else:
    cartID = request.cookies.get('cartID')
    users_cart = Cart(cartID)

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
  if user:
    users_cart = Cart.lookup_by_user(user['email'])  
  else:
    cartID = request.cookies.get('cartID')
    users_cart = Cart(cartID)

  cartItems = users_cart['items'] 
  for item in cartItems:
    item_price = users_cart.get_price(item)
    item['price'] = item_price
  totalPrice = sum(item['price'] for item in cartItems)
  
  form.version.data = users_cart['version']

  if user and hasattr(user, 'email') and not form.email.data:
    form.email.data = user.email
  
  title = "Order Summary"
  return render_template('order/order.html', title=title, cartItems=cartItems, totalPrice=totalPrice, form=form)
  

@strains_bp.route("/checkout/confirmation/<invoice_hash>", methods=['GET', 'POST'])
def order_confirmation(invoice_hash):
  order_obj = lookup_order(invoice_hash)
  if order_obj:
    order_obj["items"] = {x.split(":")[0]: float(x.split(":")[1])
                          for x in order_obj['items'].split("\n")}
    if order_obj is None:
      abort(404)
    title = "Order Confirmation"
    invoice = f"Invoice {order_obj['invoice_hash']}"
    return render_template('order/order_confirm.html', **locals())
  else:
    abort(404)
    


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
  strain_submission_url = "https://docs.google.com/forms/d/1w0VjB3jvAZmQlDbxoTx_SKkRo2uJ6TcjjX-emaQnHlQ/viewform?embedded=true"
  return render_template('strain/submission.html', **locals())