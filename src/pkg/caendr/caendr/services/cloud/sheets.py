import os
import json
import gspread

from oauth2client.service_account import ServiceAccountCredentials
from base64 import b64decode

from caendr.services.cloud.secret import get_secret


ANDERSEN_LAB_ORDER_SHEET = get_secret('ANDERSEN_LAB_ORDER_SHEET')
GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME = os.environ.get('GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME')

def get_service_account_credentials():
  """ Fetch service account credentials for google analytics """
  sa_key = b64decode(get_secret(GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME))
  return json.loads(sa_key)


def authenticate_google_sheets():
  """
    Uses service account credentials to authorize access to
    google sheets.

    In order for this to work you must share the worksheet with the google sheets service account 
    worksheet and service account name are both described in the environment config files
  """
  service_credentials = get_service_account_credentials()
  scope = ['https://spreadsheets.google.com/feeds']
  credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)
  return gspread.authorize(credentials)


def get_google_sheet(google_sheet_key, worksheet=None):
  """
    In order for this to work you must share the worksheet with the google sheets service account 
    worksheet and service account name are both described in the environment config files
  """
  gsheet = authenticate_google_sheets()
  if worksheet:
    return gsheet.open_by_key(google_sheet_key).worksheet(worksheet)
  else:
    return gsheet.open_by_key(google_sheet_key).sheet1


def get_google_order_sheet():
  """ Return the google orders spreadsheet """
  return get_google_sheet(ANDERSEN_LAB_ORDER_SHEET, 'orders')


def add_to_order_ws(row):
  """ Stores order info in a google sheet. """
  ws = get_google_order_sheet()
  index = sum([1 for x in ws.col_values(1) if x]) + 1

  header_row = filter(len, ws.row_values(1))
  values = []
  for x in header_row:
    if x in row.keys():
      values.append(row[x])
    else:
      values.append("")

  row = map(str, row)
  ws.insert_row(values, index)


def lookup_order(invoice_hash):
  """ Lookup an order by its hash """
  ws = get_google_order_sheet()
  find_row = ws.findall(invoice_hash)
  print(ws)
  if len(find_row) > 0:
    row = ws.row_values(find_row[0].row)
    header_row = ws.row_values(1)
    result = dict(zip(header_row, row))
    return {k: v for k, v in result.items() if v}
  else:
    return None

