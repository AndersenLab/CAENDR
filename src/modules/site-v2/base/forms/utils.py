from flask_wtf import FlaskForm



def _format_form_error_key(form: FlaskForm, key):
  '''
    Format a key in a form error dict for printing.
  '''
  try:
    return getattr(form, key).label.text
  except:
    return key


def _format_form_error_val(form: FlaskForm, val):
  '''
    Format a value in a form error dict for printing.
  '''
  return " ".join(val)


def format_form_errors(form: FlaskForm, format = None):
  if format is None:
    format = lambda key, val: f'{key}: {val}'

    # f'{_format_form_error_key(form, key)}: {_format_form_error_val(form, val)}'
  return [
    format(_format_form_error_key(form, key), _format_form_error_val(form, val))
      for key, val in form.errors.items()
  ]
