from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class Strain(DictSerializable, db.Model):
  species_id_method = db.Column(db.String(50), nullable=True)
  species = db.Column(db.String(50), index=True)
  species_name = db.Column(db.String(20), index=True)
  isotype_ref_strain = db.Column(db.Boolean(), index=True)
  strain = db.Column(db.String(25), primary_key=True)
  isotype = db.Column(db.String(25), index=True, nullable=True)
  previous_names = db.Column(db.String(100), nullable=True)
  sequenced = db.Column(db.Boolean(), index=True, nullable=True)  # Is whole genome sequenced [WGS_seq]
  release = db.Column(db.Integer(), nullable=False, index=True)
  source_lab = db.Column(db.String(), nullable=True)
  latitude = db.Column(db.Float(), nullable=True)
  longitude = db.Column(db.Float(), nullable=True)
  landscape = db.Column(db.String(), nullable=True)
  locality_description = db.Column(db.String(), nullable=True)
  substrate = db.Column(db.String(), nullable=True)
  substrate_comments = db.Column(db.String(), nullable=True)
  substrate_temp = db.Column(db.Float())
  ambient_temp = db.Column(db.Float())
  ambient_humidity = db.Column(db.Float())
  associated_organism = db.Column(db.String(), nullable=True)
  inbreeding_status = db.Column(db.String(), nullable=True)
  sampled_by = db.Column(db.String(), nullable=True)
  isolated_by = db.Column(db.String(), nullable=True)
  sampling_date = db.Column(db.Date(), nullable=True)
  sampling_date_comment = db.Column(db.String(), nullable=True)
  notes = db.Column(db.String(), nullable=True)
  strain_set = db.Column(db.String(), nullable=True)
  issues = db.Column(db.Boolean(), nullable=True)
  issue_notes = db.Column(db.String(), nullable=True)
  elevation = db.Column(db.Float(), nullable=True)
  
  __tablename__ = "strain"


  def __repr__(self):
    return self.strain

  @staticmethod
  def to_sortable_strain(strain):
    import re
    m = re.match('([A-Z]+)([0-9]+)', strain.strain)
    if m:
      g = m.groups()
      return (g[0], int(g[1]))
    else:
      return ('', 0)

  @staticmethod
  def sort_by_strain(arr):
    return sorted(arr, key=Strain.to_sortable_strain)


  @classmethod
  def get_columns_ordered(cls, names_only=False):
    '''
      Get the list of columns in this table, in the order specified in the source data sheet.
    '''

    # Define the column order using the column names
    col_order = [
      'species',
      'species_id_method',
      'strain',
      'isotype',
      'previous_names',
      'release',
      'source_lab',
      'latitude',
      'longitude',
      'landscape',
      'locality_description',
      'substrate',
      'substrate_comments',
      'substrate_temp',
      'ambient_temp',
      'ambient_humidity',
      'associated_organism',
      'inbreeding_state',
      'sampled_by',
      'isolated_by',
      'sampling_date',
      'sampling_date_comments',
      'notes',
      'strain_set',              # "set" in source data sheet
      'issues',
      'issue_notes',
      'isotype_ref_strain',
      'sequenced',               # "wgs_seq" in source data sheet
      # 'peel-zeel',
      # 'pha-sup',
      # 'nagoya',
    ]

    # Get the list of columns, associated with their index in the ordered list
    col_list = [
      (col_order.index(c.name) if c.name in col_order else None, c)
        for c in list(cls.__mapper__.columns)
    ]

    # Filter out any columns not in the ordered list
    col_list = [ c for c in col_list if c[0] is not None]

    # Sort by index in ordered list, and map back to just the column object
    col_list = [ c[1] for c in sorted(col_list, key=lambda x: x[0]) ]

    # Return names or full columns, as requested
    # Can't just return ordered list above because some of the columns listed are not defined in this table
    if names_only:
      return [ c.name for c in col_list ]
    else:
      return col_list
