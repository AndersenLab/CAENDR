from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class Species(DictSerializable, db.Model):
  '''
    Species [ORM for different Species of nematode]
      Args:
        DictSerializable (object): [Class with method for serializing an ORM as a Dict]
        db (object): [Base model for sqlalchemy ORM]
  '''
  __tablename__ = "species"
  
  id = db.Column(db.SmallInteger, primary_key=True)
  species_str = db.Column(db.String(50), index=True, unique=True)

  __species_str_constraint__ = db.UniqueConstraint(species_str)
