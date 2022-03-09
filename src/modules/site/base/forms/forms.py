import json
import pandas as pd
import numpy as np
from logzero import logger


from flask_wtf import FlaskForm, RecaptchaField, Form
from wtforms import (StringField,
                     DateField,
                     BooleanField,
                     TextAreaField,
                     IntegerField,
                     SelectField,
                     SelectMultipleField,
                     widgets,
                     FieldList,
                     HiddenField,
                     RadioField)

from wtforms.fields.simple import PasswordField
from wtforms.validators import (Required, 
                                Length, 
                                Email, 
                                DataRequired, 
                                EqualTo, 
                                Optional,
                                ValidationError)
from wtforms.fields.html5 import EmailField


from constants import PRICES, SECTOR_OPTIONS, SHIPPING_OPTIONS, PAYMENT_OPTIONS, REPORT_TYPES

from caendr.services.profile import get_profile_role_form_options
from caendr.services.user import get_user_role_form_options
from caendr.services.database_operation import get_db_op_form_options
from caendr.services.indel_primer import get_indel_primer_chrom_choices, get_indel_primer_strain_choices
from caendr.services.markdown import get_content_type_form_options
from caendr.models.datastore import User
from caendr.api.strain import query_strains
from base.forms.validators import (validate_duplicate_strain, 
                                   validate_duplicate_isotype, 
                                   validate_row_length, 
                                   validate_isotypes, 
                                   validate_numeric_columns, 
                                   validate_column_name_exists, 
                                   validate_column_names, 
                                   validate_unique_colnames, 
                                   validate_report_name_unique, 
                                   validate_missing_isotype, 
                                   validate_strain_w_no_data, 
                                   validate_data_exists,
                                   validate_start_lt_stop,
                                   validate_uniq_strains)


class MultiCheckboxField(SelectMultipleField):
  widget = widgets.ListWidget(prefix_label=False)
  option_widget = widgets.CheckboxInput() 

class EmptyForm(FlaskForm):
  pass

class FileUploadForm(FlaskForm):
  pass

class HeritabilityForm(Form):
  pass

class VBrowserForm(FlaskForm):
  pass


class BasicLoginForm(FlaskForm):
  """ The simple username/password login form """
  username = StringField('Username', [Required(), Length(min=5, max=30)])
  password = PasswordField('Password', [Required(), Length(min=5, max=30)])
  recaptcha = RecaptchaField()


class MarkdownForm(FlaskForm):
  """ markdown editing form """
  _CONTENT_TYPES = get_content_type_form_options()

  title = StringField('Title', [Optional()])
  content = StringField('Content', [Optional()])
  type = SelectField('Type', choices=_CONTENT_TYPES, validators=[Required()])


class UserRegisterForm(FlaskForm):
  """ Register as a new user with username/password """
  username = StringField('Username', [Required(), Length(min=5, max=30)])
  full_name = StringField('Full Name', [Required(), Length(min=5, max=50)])
  email = EmailField('Email Address', [Required(), Email(), Length(min=6, max=50)])
  password = PasswordField('Password', [Required(), EqualTo('confirm_password', message='Passwords must match'), Length(min=5, max=30)])
  confirm_password = PasswordField('Confirm Password', [Required(), EqualTo('password', message='Passwords must match'), Length(min=5, max=30)])
  recaptcha = RecaptchaField()

  def validate_username(form, field):
    user = User(field.data)
    if user._exists:
      raise ValidationError("Username already exists")


class UserUpdateForm(FlaskForm):
  """ Modifies an existing users profile """
  full_name = StringField('Full Name', [Required(), Length(min=5, max=50)])
  email = EmailField('Email Address', [Required(), Email(), Length(min=6, max=50)])
  password = PasswordField('Password', [Optional(), EqualTo('confirm_password', message='Passwords must match'), Length(min=5, max=30)])
  confirm_password = PasswordField('Confirm Password', [Optional(), EqualTo('password', message='Passwords must match'), Length(min=5, max=30)])


class AdminEditUserForm(FlaskForm):
  """ A form for one or more roles """
  _USER_ROLES = get_user_role_form_options()

  roles = MultiCheckboxField('User Roles', choices=_USER_ROLES)

class AdminEditProfileForm(FlaskForm):
  """ A form for updating individuals' public profile on the site """
  _PROFILE_ROLES = get_profile_role_form_options()
  
  first_name = StringField('First Name', [Required(), Length(min=1, max=50)])
  last_name = StringField('Last Name', [Required(), Length(min=1, max=50)])
  title = StringField('Staff Title', [Optional(), Length(min=1, max=50)])
  org = StringField('Organization', [Optional(), Length(min=1, max=50)])
  email = StringField('Email', [Email(), Optional(), Length(min=3, max=100)])
  website = StringField('Website', [Optional(), Length(min=3, max=200)])
  prof_roles = MultiCheckboxField('Profile Pages', choices=_PROFILE_ROLES)


class AdminCreateDatabaseOperationForm(FlaskForm):
  _ops = get_db_op_form_options()
  
  db_op = SelectField('Database Operation', choices=_ops, validators=[Required()])
  wormbase_version = IntegerField('Wormbase Version WS (ex: 276 -> WS276):', validators=[Optional()])
  sva_version = IntegerField('Strain Variant Annotation Version (ex: 20210401 -> gs://caendr-db-bucket/strain_variant_annotation/c_elegans/WI.strain-annotation.bcsq.20210401.csv.gz)', validators=[Optional()])
  note = StringField('Notes', [Optional(), Length(min=3, max=200)])



class AdminGeneBrowserTracksForm(FlaskForm):  
  wormbase_version = IntegerField('Wormbase Version WS (ex: 276 -> WS276):', validators=[Optional()])
  note = StringField('Notes', [Optional(), Length(min=3, max=200)])


class AdminEditToolContainerVersion(FlaskForm):
  version = SelectField('Container Version Tag', validators=[Required()])
  
class DatasetReleaseForm(FlaskForm):
  """ A form for creating a data release """
  version = IntegerField('Dataset Release Version', validators=[Required(message="Dataset release version (as an integer) is required (ex: 20210121)")])
  wormbase_version = IntegerField('Wormbase Version WS:', validators=[Required(message="Wormbase version (as an integer) is required (ex: WS276 -> 276)")])
  report_type = SelectField('Report Type', choices=REPORT_TYPES, validators=[Required()])
  disabled = BooleanField('Disabled')
  hidden = BooleanField('Hidden')


class DonationForm(Form):
  """ The donation form """
  name = StringField('Name', [Required(), Length(min=3, max=100)])
  address = TextAreaField('Address', [Length(min=10, max=200)])
  email = StringField('Email', [Email(), Length(min=3, max=100)])
  total = IntegerField('Donation Amount')
  recaptcha = RecaptchaField()


class FlexIntegerField(IntegerField):
  def process_formdata(self, val):
    if val:
      val[0] = val[0].replace(",", "").replace(".", "")
    return super(FlexIntegerField, self).process_formdata(val)


class PairwiseIndelForm(Form):
  STRAIN_CHOICES = get_indel_primer_strain_choices()
  CHROMOSOME_CHOICES = get_indel_primer_chrom_choices()
  
  strain_1 = SelectField('Strain 1', choices=STRAIN_CHOICES, default="N2", validators=[Required(), validate_uniq_strains])
  strain_2 = SelectField('Strain 2', choices=STRAIN_CHOICES, default="CB4856", validators=[Required()])
  chromosome = SelectField('Chromosome', choices=CHROMOSOME_CHOICES, default="V", validators=[Required()])
  start = FlexIntegerField('Start', default="6,271,913", validators=[Required(), validate_start_lt_stop])
  stop = FlexIntegerField('Stop', default="6,272,025", validators=[Required()])

  
class OrderForm(Form):
  """ The strain order form """
  sector = SelectField('Sector', choices=SECTOR_OPTIONS, default="academia")
  name = StringField('Name', [Required(), Length(min=3, max=100)])
  email = StringField('Email', [Email(), Length(min=3, max=100)])
  address = TextAreaField('Address', [Length(min=10, max=200)])
  phone = StringField('Phone', [Length(min=3, max=35)])
  shipping_service = SelectField('Shipping', choices=SHIPPING_OPTIONS)
  shipping_account = StringField('Account Number')
  items = FieldList(HiddenField('item', [DataRequired()]))
  payment = SelectField("Payment", choices=PAYMENT_OPTIONS)
  comments = TextAreaField("Comments", [Length(min=0, max=300)])
  #recaptcha = RecaptchaField()

  def validate_shipping_account(form, field):
    """ Ensure the user supplies an account number when appropriate. """
    if form.shipping_service.data != "Flat Rate Shipping" and not field.data:
      raise ValidationError("Please supply a shipping account number.")
    elif form.shipping_service.data == "Flat Rate Shipping" and field.data:
      raise ValidationError("No shipping account number is needed if you are using flat-rate shipping.")

  def item_price(self):
    """ Fetch item and its price """
    for item in self.items:
      if item.data == "set_divergent":
        yield item.data, PRICES.DIVERGENT_SET
      elif item.data.startswith("set"):
        yield item.data, PRICES.STRAIN_SET
      else:
        yield item.data, PRICES.STRAIN
    if self.shipping_service.data == "Flat Rate Shipping":
      yield "Flat Rate Shipping", PRICES.SHIPPING

  @property
  def total(self):
    """ Calculates the total price of the order """
    total_price = 0
    for item, price in self.item_price():
      total_price += price
    return total_price


class TraitData(HiddenField):
  """ A subclass of HiddenField is used to do the initial processing of the data
      input from the 'handsontable' structure on the perform mapping page. """
  def process_formdata(self, input_data):
    if input_data:
      self.data = input_data[0]
    else:
      self.data = None
      self.processed_data = None
      return

    self.error_items = []  # Cells to highlight as having errors

    try:
      data = json.loads(input_data[0])
    except ValueError as e:
      raise ValidationError(e.msg)

    # Read in data
    headers = data.pop(0)
    df = pd.DataFrame(data, columns=headers) \
      .replace('', np.nan) \
      .dropna(how='all') \
      .dropna(how='all', axis=1)
    if 'STRAIN' in df.columns:
      self.strain_list = list(df.STRAIN)

    # Resolve isotypes and insert as second column
    try:
      df = df.assign(ISOTYPE=[query_strains(x, resolve_isotype=True) for x in df.STRAIN])
      isotype_col = df.pop("ISOTYPE")
      df.insert(1, "ISOTYPE", isotype_col)
      logger.info(df)
    except AttributeError:
      # If the user fails to pass data it will be flagged
      pass
    
    self.processed_data = df


# This form isnt being used to submit to  the new pipeline but this validator code 
# will prove useful in the future.
class MappingSubmissionForm(Form):
  """ Form for mapping submission """
  report_name = StringField('Report Name', [Required(),
                                            Length(min=1, max=50),
                                            validate_report_name_unique])
  is_public = RadioField('Release', choices=[('true', 'public'), ('false', 'private')])
  description = TextAreaField('Description', [Length(min=0, max=1000)])
  trait_data = TraitData(validators=[validate_row_length,
                                      validate_duplicate_strain,
                                      validate_duplicate_isotype,
                                      validate_isotypes,
                                      validate_numeric_columns,
                                      validate_column_names,
                                      validate_unique_colnames,
                                      validate_column_name_exists,
                                      validate_missing_isotype,
                                      validate_strain_w_no_data,
                                      validate_data_exists])


