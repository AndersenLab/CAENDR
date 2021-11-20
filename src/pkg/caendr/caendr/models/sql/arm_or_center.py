from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class ArmOrCenter(DictSerializable, db.Model):
  '''
    ArmOrCenter [ORM for ArmOrCenter]
      Args:
        DictSerializable (object): [Class with method for serializing an ORM as a Dict]
        db (object): [Base model for sqlalchemy ORM]
  '''
  __tablename__ = "arm_or_center"
  
  id = db.Column(db.SmallInteger, primary_key=True)
  arm_or_center_str = db.Column(db.String(7), index=True, unique=True, null=True)

  __arm_or_center_str_constraint__ = db.UniqueConstraint(arm_or_center_str)

