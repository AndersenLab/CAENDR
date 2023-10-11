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
      carts = cls.query_ds_not_deleted('user', email, required=True)
      if len(carts) == 1:
        # If only one cart was found, return it
        return carts[0]
      else:
        # If multiple carts found for user, sort by date modified on and return latest
        return cls.sort_by_modified_date(carts, reverse=True)[0]

    # If a user doesn't have a cart, create one
    except NotFoundError:
      return Cart(**{'user': email, 'items': [], 'version': 0})


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
      if cartItem['name'] == item['name']:
        return
    self['items'].append(item)


  def remove_item(self, item):
    for cartItem in self['items']:
      if cartItem['name'] == item:
        self['items'].remove(cartItem)

  def update_version(self):
    self['version'] += 1

  # def soft_delete(self):
  #   self['is_deleted'] = True







# class Cart(Entity):
#   kind = 'cart'

#   def __init__(self, name_or_obj = None, *args, **kwargs): # If nothing passed for name_or_obj, create a new ID to use for this object
#     if name_or_obj is None: 
#       name_or_obj = unique_id()
#       self.set_properties_meta(id = name_or_obj) 

#   # Initialize from superclass 
#     super().__init__(name_or_obj, *args, **kwargs)
#     if not self['is_deleted']:
#       self['is_deleted'] = False
#     if not self['items']:
#       self['items'] = []
#     if not self['version']:
#       self['version'] = 0
  
#   ## Properties List ##

#   @classmethod
#   def get_props_set(cls):
#     return {
#       *super().get_props_set(),
#       'user',
#       'items',
#       'is_deleted',
#       'version'
#     }
  
  

#   @classmethod
#   def lookup_by_user(cls, email):

#     # Try finding and returning unique cart for this user
#     try:
#       return Cart.query_ds_not_deleted('user', email, required=True)


#     # If a user doesn't have a cart, create one
#     except NotFoundError:
#       return Cart(**{'user': email, 'items': [], 'version': 0})

#     # Multiple carts found for user
#     # TODO: get all carts that match the user, sort by date created on and return the latest one?
#     except NonUniqueEntity as ex:
#       return Cart.sort_by_modified_date(ex.matches, reverse=True)[0]


#   @classmethod
#   def get_price(self, item):
#     if item['name'] == 'Flat Rate Shipping':
#       return PRICES.SHIPPING
#     elif item['name'] == "set_divergent":
#       return PRICES.DIVERGENT_SET
#     elif item['name'].startswith("set"):
#       return PRICES.STRAIN_SET
#     else:
#       return PRICES.STRAIN


#   def transfer_to_user(self, email):
#     self['user'] = email


#   def add_item(self, item):
#     for cartItem in self['items']:
#       if cartItem['name'] == item['name']:
#         return
#     self['items'].append(item)


#   def remove_item(self, item):
#     for cartItem in self['items']:
#       if cartItem['name'] == item:
#         self['items'].remove(cartItem)


#   def soft_delete(self):
#     self['is_deleted'] = True

#   def update_version(self):
#     self['version'] += 1


