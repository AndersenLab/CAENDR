from slugify import slugify
from wtforms.validators import ValidationError
from logzero import logger
from gcloud.exceptions import BadRequest

from caendr.services.cloud.datastore import get_ds_entity
from caendr.utils.data import is_number, list_duplicates


def validate_duplicate_strain(form, field):
  """ Validates that each there are no duplicate strains listed. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    # Only raise this error once.
    raise ValidationError("Problem with column")
  try:
    dup_strains = df.STRAIN[df.STRAIN.duplicated()]
    if dup_strains.any():
      dup_strains = dup_strains.values
      form.trait_data.error_items.extend(dup_strains)
      raise ValidationError(f"Duplicate Strains: {dup_strains}")
  except AttributeError:
    pass


def validate_duplicate_isotype(form, field):
  """  Validates that each strain has a single associated isotype. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  try:
    dup_isotypes = df.STRAIN[df.ISOTYPE.duplicated()]
    if dup_isotypes.any():
      dup_isotypes = dup_isotypes.values
      form.trait_data.error_items.extend(dup_isotypes)
      raise ValidationError(f"Some strains belong to the same isotype: {dup_isotypes}")
  except AttributeError:
    pass


def validate_row_length(form, field):
  """ Validates that a minimum of 30 strains are present. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  invalid_len_columns = [x for x in df.columns[2:] if df[x].notnull().sum() < 30]
  if invalid_len_columns:
    form.trait_data.error_items.extend(invalid_len_columns)
    raise ValidationError(f"A minimum of 30 strains are required. Need more values for trait(s): {invalid_len_columns}")


def validate_col_length(form, field):
  """ Validates there are no more than 5 traits. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  rows, columns = df.shape
  if columns > 5:
    raise ValidationError("Only five traits can be submitted")


def validate_isotypes(form, field):
  """ Validates that isotypes are resolved. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  try:
    unknown_strains = df.STRAIN[df.ISOTYPE.isnull()]
    if unknown_strains.any():
      unknown_strains = unknown_strains.values
      form.trait_data.error_items.extend(unknown_strains)
      raise ValidationError(f"Unknown isotype for the following strain(s): {unknown_strains}")
  except AttributeError:
    pass


def validate_numeric_columns(form, field):
  """ Validates that trait fields are numeric """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  non_numeric_values = []
  try:
    for x in df.columns[2:]:
      if any(df[x].map(is_number) == False):
        non_numeric_values.extend(df[x][df[x].map(is_number) == False].tolist())
    if non_numeric_values:
      form.trait_data.error_items.extend(non_numeric_values)
      raise ValidationError(f"Trait(s) have non-numeric values: {non_numeric_values}")
  except AttributeError:
      raise ValidationError(f"Trait names specified incorrectly")


def validate_column_name_exists(form, field):
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  for n, x in enumerate(df.columns[2:]):
    if not x:
      raise ValidationError(f"Missing trait name in column {n+2}")


def validate_column_names(form, field):
  """ Validates that the variable names are safe for R """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  for x in df.columns[2:]:
    malformed_cols = [x for x in df.columns[2:] if slugify(x).lower() != x.lower() and slugify(x)]
    if malformed_cols:
      form.trait_data.error_items.extend(malformed_cols)
      raise ValidationError(f"Trait names must begin with a letter and can only contain letters, numbers, dashes, and underscores. These columns need to be renamed: {malformed_cols}")


def validate_unique_colnames(form, field):
  """ Validates that column names are unique. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  duplicate_col_names = list_duplicates(df.columns[1:])
  if duplicate_col_names:
    form.trait_data.error_items.extend(duplicate_col_names)
    raise ValidationError(f"Duplicate column names: {duplicate_col_names}")


def validate_report_name_unique(form, field):
  """ Checks to ensure that the report name submitted is unique. """
  report_slug = slugify(form.report_name.data)
  try:
    reports = get_ds_entity('trait', filters=[('report_slug', '=', report_slug)])
    if len(reports) > 0:
      raise ValidationError(f"That report name is not available. Choose a unique report name")
  except BadRequest:
    raise ValidationError(f"Backend Error")


def validate_missing_isotype(form, field):
  """ Checks to see whether data is provided for an isotype that does not exist. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  try:
    blank_strains = list(df[df.STRAIN.isnull()].apply(lambda row: sum(row.isnull()), axis=1).index+1)
    if blank_strains:
      raise ValidationError(f"Missing strain(s) on row(s): {blank_strains}")
  except AttributeError:
    pass


def validate_strain_w_no_data(form, field):
  """ Checks to see whether any strains are present that have no associated trait data. """
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  null_counts = df.apply(lambda row: sum(row.isnull()), axis=1)
  missing_trait_data = (len(df.columns) - null_counts == 2)
  try:
    blank_traits = list(df[missing_trait_data & df.STRAIN.notnull() == True].STRAIN)
    if blank_traits:
      raise ValidationError(f"Strain(s) with no trait data: {blank_traits}")
  except AttributeError:
    pass


def validate_data_exists(form, field):
  try:
    df = form.trait_data.processed_data
  except AttributeError:
    return
  logger.info(df)
  try:
    df.STRAIN
    df.ISOTYPE
  except AttributeError:
    raise ValidationError("No data provided")

