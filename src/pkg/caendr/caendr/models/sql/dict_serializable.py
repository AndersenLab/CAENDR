class DictSerializable(object):
  def _asdict(self):
    result = {}
    for key in self.__mapper__.c.keys():
      result[key] = getattr(self, key)
    return result

  def to_json(self):
    return {k: v for k, v in self._asdict().items() if not k.startswith("_")}
