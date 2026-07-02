import re
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable
from caendr.utils.constants import STRAIN_NAME_REGEX

class Strain(DictSerializable, db.Model):
  species_id_method: Mapped[str | None] = mapped_column(String(50))
  species: Mapped[str] = mapped_column(String(50), index=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True)
  isotype_ref_strain: Mapped[bool] = mapped_column(Boolean(), index=True)
  strain: Mapped[str] = mapped_column(String(25), primary_key=True)
  isotype: Mapped[str | None] = mapped_column(String(25), index=True)
  previous_names: Mapped[str | None] = mapped_column(String(100))
  sequenced: Mapped[bool | None] = mapped_column(Boolean(), index=True)  # Is whole genome sequenced [WGS_seq]
  release: Mapped[int] = mapped_column(Integer(), index=True)
  source_lab: Mapped[str | None] = mapped_column(String())
  latitude: Mapped[float | None] = mapped_column(Float())
  longitude: Mapped[float | None] = mapped_column(Float())
  landscape: Mapped[str | None] = mapped_column(String())
  locality_description: Mapped[str | None] = mapped_column(String())
  substrate: Mapped[str | None] = mapped_column(String())
  substrate_comments: Mapped[str | None] = mapped_column(String())
  substrate_temp: Mapped[float | None] = mapped_column(Float())
  ambient_temp: Mapped[float | None] = mapped_column(Float())
  ambient_humidity: Mapped[float | None] = mapped_column(Float())
  associated_organism: Mapped[str | None] = mapped_column(String())
  inbreeding_state: Mapped[str | None] = mapped_column(String())
  sampled_by: Mapped[str | None] = mapped_column(String())
  isolated_by: Mapped[str | None] = mapped_column(String())
  sampling_date: Mapped[datetime | None] = mapped_column(DateTime())
  sampling_date_comments: Mapped[str | None] = mapped_column(String())
  notes: Mapped[str | None] = mapped_column(String())
  strain_set: Mapped[str | None] = mapped_column(String())
  issues: Mapped[bool | None] = mapped_column(Boolean())
  issue_notes: Mapped[str | None] = mapped_column(String())
  elevation: Mapped[float | None] = mapped_column(Float())
  distribute: Mapped[bool] = mapped_column(Boolean())
  wgs_seq: Mapped[bool] = mapped_column(Boolean())

  __tablename__ = "strain"


  def __repr__(self):
    return self.strain

  @staticmethod
  def to_sortable_strain(strain):
    m = re.match(STRAIN_NAME_REGEX, strain.strain)
    if m:
      return (m.group(1), int(m.group(2)))
    return ('', 0)

  @staticmethod
  def sort_by_strain(arr):
    return sorted(arr, key=Strain.to_sortable_strain)

  @staticmethod
  def to_sortable_isotype(strain):
    m = re.match(STRAIN_NAME_REGEX, strain.strain)
    if m:
      return (m.group(1), int(m.group(2)))
    return ('', 0)


  @classmethod
  def get_column_names_ordered(cls):
    '''
      Get the list of column names in this table, in the order specified in the source data sheet.
    '''
    return [ c.name for c in cls.get_columns_ordered() ]


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
      'strain_set', # set in spreadsheet
      'issues',
      'issue_notes',
      'isotype_ref_strain',
      'wgs_seq',
      'distribute',
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

    # Return columns
    return col_list
