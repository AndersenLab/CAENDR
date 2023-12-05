from caendr.models.datastore import DeletableEntity
from caendr.models.error import NotFoundError, NonUniqueEntity
from caendr.utils.data import unique_id

class PRICES:
  DIVERGENT_SET = 160
  STRAIN_SET = 640
  STRAIN = 15
  SHIPPING = 65


class Cart(DeletableEntity):
  kind = 'cart'

  def __init__(self, name_or_obj = None, *args, **kwargs): # If nothing passed for name_or_obj, create a new ID to use for this object
    if name_or_obj is None: 
      name_or_obj = unique_id()
      self.set_properties_meta(id = name_or_obj) 

  # Initialize from superclass 
    super().__init__(name_or_obj, *args, **kwargs)
    if not self['items']:
      self['items'] = []
    if not self['version']:
      self['version'] = 0

  # Get the number of items in the cart
  def __len__(self):
    return len(self['items'])
  
  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'user',
      'items',
      'version'
    }
  
  

  @classmethod
  def lookup_by_user(cls, email):
    
    # Try finding cart(s) for user
    try:
      # Run the query and try to find not deleted cart(s) for the user
      carts = cls.query_ds_not_deleted('user', email, required=True)

      # If one cart was found, return it
      # Or if multiple carts were found, sort by date modified on and return latest
      return cls.sort_by_modified_date(carts, reverse=True)[0]

    # If a user doesn't have a cart, create one
    except NotFoundError:
      return Cart.create_for_user(email)

  @classmethod
  def create_for_user(cls, email):
    return cls(**{'user': email})


  @classmethod
  def get_price(self, item):
    if item['name'] == 'Flat Rate Shipping':
      return PRICES.SHIPPING
    elif item['name'] == "set_divergent":
      return PRICES.DIVERGENT_SET
    elif item['name'].startswith("set"):
      return PRICES.STRAIN_SET
    else:
      return PRICES.STRAIN


  def transfer_to_user(self, email):
    self['user'] = email


  def add_item(self, item):
    for cartItem in self['items']:
      if cartItem['name'] == item['name'] and cartItem['species'] == item['species']:
        return
    self['items'].append(item)


  def remove_item(self, item):
    for cartItem in self['items']:
      if cartItem['name'] == item['name'] and cartItem['species'] == item['species']:
        self['items'].remove(cartItem)

  def update_version(self):
    self['version'] += 1