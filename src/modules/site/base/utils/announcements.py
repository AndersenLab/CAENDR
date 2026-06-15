from functools import wraps

from flask import g



def block_announcements(f):
  '''
    Prevent an endpoint from flashing site-wide announcements.
  '''
  @wraps(f)
  def decorator(*args, **kwargs):
    try:
      g.block_site_announcements = True
    except:
      pass
    return f(*args, **kwargs)
  return decorator


def block_announcements_from_bp(bp):
  '''
    Prevent all endpoints in the given blueprint from flashing site-wide announcements.
  '''
  @bp.before_request
  def _block_announcements():
    g.block_site_announcements = True
