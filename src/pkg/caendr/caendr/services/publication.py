from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.sheets import get_public_google_sheet_as_df

from caendr.models.error import GoogleSheetsParseError

CENDR_PUBLICATIONS_SHEET = get_secret('CENDR_PUBLICATIONS_SHEET')

def get_publications_html_df():
  df = get_public_google_sheet_as_df(CENDR_PUBLICATIONS_SHEET)
  try:
    df['pmid'] = df['pmid'].astype(int)
    df = df.sort_values(by='pmid', ascending=False)
    df = df.apply(lambda x: f"""<strong><a href="{x.url}">{x.title.strip(".")}</a>
                                </strong><br />
                                {x.authors}<br />
                                ( {x.pub_date} ) <i>{x.journal}</i>""", axis = 1)
    df = list(df.values)[:-1]
    return df
  except:
    raise GoogleSheetsParseError(f'Error parsing Publications Sheet: {CENDR_PUBLICATIONS_SHEET}')

