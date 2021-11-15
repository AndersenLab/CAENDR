from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class DictSerializable(object):
  def _asdict(self):
    result = {}
    for key in self.__mapper__.c.keys():
      result[key] = getattr(self, key)
    return result
