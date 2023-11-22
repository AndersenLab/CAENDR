from dateutil import parser
from caendr.services.logger import logger



elevation_cache = {}
NULL_VALS = ["None", "", "NA", None]


# Local get_elevation import because this module is now used in the site
# (to check required files for database operations),
# but DiskCache (imported by services.elevation) is not used in the site.
# TODO: Fix, somehow... Do we even need DiskCache? We're already caching in this file
def fetch_elevation(lat, lon):
  from caendr.services.elevation import get_elevation

  key = f'{lat}_{lon}'
  elevation = elevation_cache.get(key, None)
  if not elevation:
    elevation = get_elevation(lat, lon)
    if elevation:
      elevation_cache[key] = elevation
  
  return elevation


def fetch_andersen_strains(species, STRAINS):
  """
    Fetches latest strains from
    google sheet database.

    - NA values are converted to NULL
    - Datetime values are parsed
    - Strain sets are concatenated with ','
    - Fetches elevation for each strain
  """

  # Get records from Google sheet
  strain_records = STRAINS.get_all_records()

  # Only take records with a release reported
  strain_records = list(filter(lambda x: x.get('release') not in NULL_VALS, strain_records))

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

    # Store the species name identifier
    record['species_name'] = species.name

    # Yield the record to be appended to the db
    yield record
