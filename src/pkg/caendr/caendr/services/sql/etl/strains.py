from dateutil import parser
from caendr.services.logger import logger

from caendr.services.elevation import get_elevation
from caendr.services.cloud.sheets import get_google_sheet
from caendr.services.cloud.secret import get_secret
from caendr.models.datastore import Species
from caendr.models.sql import Strain

# Get list of Google Sheet IDs for each species
# Expects secret names with prefix "ANDERSEN_LAB_STRAIN_SHEET_"
# and species ID in all caps
ANDERSEN_LAB_STRAIN_SHEETS = {
  species_name: get_secret(f'ANDERSEN_LAB_STRAIN_SHEET_{species_name.upper()}')
    for species_name in Species.all()
}

elevation_cache = {}
NULL_VALS = ["None", "", "NA", None]

def load_strains(db, species=None):
  logger.info('Loading strains...')

  # Filter sheets to match species list, or use all if no list provided
  sheet_list = [
    val for key, val in ANDERSEN_LAB_STRAIN_SHEETS.items() if (species is None or key in species)
  ]

  for sheet_id in sheet_list:
    andersen_strains = fetch_andersen_strains(sheet_id)
    db.session.bulk_insert_mappings(Strain, andersen_strains)
    db.session.commit()
  logger.info(f"Inserted {Strain.query.count()} strains")
  

def fetch_elevation(lat, lon):
  key = f'{lat}_{lon}'
  elevation = elevation_cache.get(key, None)
  if not elevation:
    elevation = get_elevation(lat, lon)
    if elevation:
      elevation_cache[key] = elevation
  
  return elevation


def fetch_andersen_strains(sheet_id: str):
  """
    Fetches latest strains from
    google sheet database.

    - NA values are converted to NULL
    - Datetime values are parsed
    - Strain sets are concatenated with ','
    - Fetches elevation for each strain
  """

  # Get records from Google sheet
  WI = get_google_sheet(sheet_id)
  strain_records = WI.get_all_records()

  # Only take records with a release reported
  strain_records = list(filter(lambda x: x.get('release') not in NULL_VALS, strain_records))

  results = []
  for n, record in enumerate(strain_records):
    record = {k.lower(): v for k, v in record.items()}
    for k, v in record.items():
      # Set NA to None
      if v in NULL_VALS:
        v = None
        record[k] = v
      if k in ['sampling_date'] and v:
        record[k] = parser.parse(v)

    if record['latitude'] and record['longitude']:
      # Round elevation
      elevation = fetch_elevation(record['latitude'], record['longitude'])
      if elevation:
        record['elevation'] = round(elevation)
    if n % 50 == 0:
      logger.debug(f"Loaded {n} strains")

    # Set issue bools
    record["issues"] = record["issues"] == "TRUE"

    # Set isotype_ref_strain = FALSE if no isotype is assigned.
    if record['isotype'] in NULL_VALS:
      record['isotype_ref_strain'] = False
      record['wgs_seq'] = False

    # Skip strains that lack an isotype
    if record['isotype'] in NULL_VALS and record['issues'] is False:
      continue

    # Fix strain reference
    record['isotype_ref_strain'] = record['isotype_ref_strain'] == "TRUE"
    record['sequenced'] = record['wgs_seq'] == "TRUE"

    # set (python built-in) --> strain_set
    record['strain_set'] = record['set']

    # Remove space after comma delimiter
    if record['previous_names']:
      record['previous_names'] = str(record['previous_names']).replace(", ", ",").strip()
    results.append(record)

    # Convert species scientific name to species ID string
    record['species_name'] = f"c_{record['species'].split(' ')[1]}"

  return results