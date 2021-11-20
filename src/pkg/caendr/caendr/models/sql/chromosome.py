from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class ChromosomeSummary(DictSerializable, db.Model):
  '''
    ChromosomeSummary [ORM for Chromosomes]
      Args:
        DictSerializable (object): [Class with method for serializing an ORM as a Dict]
        db (object): [Base model for sqlalchemy ORM]
  '''
  __tablename__ = "chromosome"
  
  id = db.Column(db.SmallInteger, primary_key=True)
  chrom_int = db.Column(db.SmallInteger, index=True, unique=True)
  chrom_str = db.Column(db.String(7), index=True, unique=True)

  __chrom_int_constraint__ = db.UniqueConstraint(chrom_int)
  __chrom_str_constraint__ = db.UniqueConstraint(chrom_str)

