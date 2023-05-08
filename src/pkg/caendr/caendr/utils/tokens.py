from string import Template

from caendr.models.error import InvalidTokenError, MissingTokenError


class TokenizedString():

  def __init__(self, template):

    # Initialize empty dict of tokens
    self.tokens = {}

    # Get argument as a string template
    self.update_template_string(template)


  def copy_with_tokens(self, **kwargs):
    '''
      Create a copy of this tokenized string, carrying over all set tokens.
    '''
    return TokenizedString(self.template).set_tokens(**kwargs)
  

  def __repr__(self):
    if len(self.raw_string) <= 15:
      return f'<TokenizedString: {self.raw_string}>'
    else:
      return f'<TokenizedString: {self.raw_string[:12]}...>'
    

  def __str__(self):
    return self.raw_string



  #
  # Setting / Updating Template String
  #

  def update_template_string(self, template):
    '''
      Set the template string directly.
    '''
    if isinstance(template, str):
      self.template = Template(template)
    elif isinstance(template, Template):
      self.template = template
    else:
      raise ValueError(f'Cannot replace tokens in non-string value {template}')
    return self


  def __add__(self, other):
    '''
      Use '+' operator to update the template string directly.
    '''

    # String - add directly to template
    if isinstance(other, str):
      return TokenizedString(self.raw_string + other).set_tokens(**self.tokens)
    
    # Template - add template string directly
    elif isinstance(other, Template):
      return TokenizedString(self.raw_string + other.template).set_tokens(**self.tokens)
    
    # Tokenized String - add templates, throwing error if token sets conflict
    elif isinstance(other, TokenizedString):
      for key in self.tokens:
        if key in other.tokens and self.tokens[key] != other.tokens[key]:
          raise InvalidTokenError(key)
      return TokenizedString(self.raw_string + other.raw_string).set_tokens(**{**self.tokens, **other.tokens})
    
    # Other - throw error
    else:
      raise ValueError(f'Cannot replace tokens in non-string value {other}')



  #
  # Validation
  #

  VALID_TOKENS = {
    'SPECIES',
    'RELEASE',
    'PRJ',
    'WB',
    'SVA',
    'STRAIN',
  }

  @classmethod
  def is_valid_token(cls, key):
    return key in cls.VALID_TOKENS

  @classmethod
  def validate_tokens(cls, **kwargs):
    for key in kwargs:
      if not cls.is_valid_token(key):
        raise InvalidTokenError(key)



  #
  # Setting Tokens
  #


  def set_tokens(self, **kwargs):
    for key, val in kwargs.items():
      if self.is_valid_token(key):
        self.tokens[key] = val
      else:
        raise InvalidTokenError(key)
    return self



  #
  # String Conversion
  #


  def get_string(self, **kwargs):
    '''
      Apply all token replacements, throwing an error if any tokens remain unset.
    '''
    self.validate_tokens(**kwargs)
    try:
      return self.template.substitute(**{**self.tokens, **kwargs})
    except:
      raise MissingTokenError()


  def get_string_safe(self, **kwargs):
    '''
      Apply all token replacements, ignoring any tokens that are unset.
    '''
    self.validate_tokens(**kwargs)
    return self.template.safe_substitute(**{**self.tokens, **kwargs})


  @property
  def raw_string(self):
    '''
      Get the raw template string, without any replacements.
    '''
    # TODO: Make sure braces are included around tokens? For JS compatibility
    return self.template.template




# def replace_tokens_recursive(obj, **kwargs):
#   if isinstance(obj, str):
#     return replace_species_tokens(obj, **kwargs)
#   elif isinstance(obj, dict):
#     return { key: replace_tokens_recursive(val, **kwargs) for key, val in obj.items() }
#   else:
#     return obj