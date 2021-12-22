
def verify_cron_req_origin(request):
  cron_header = request.headers.get('X-Appengine-Cron')
  if cron_header:
    return True
  return False
