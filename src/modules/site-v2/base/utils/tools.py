from base.utils.auth import get_current_user, user_is_admin

from caendr.models.error import ReportLookupError


def validate_report(report, user=None):

  # If no user explicitly provided, default to current user
  if user is None:
    user = get_current_user()

  # If no such report exists, show an error message
  if report is None:

    # Let admins know the report doesn't exist
    if user_is_admin():
      raise ReportLookupError('This report does not exist', 404)

    # For all other users, display a default "no access" message
    else:
      raise ReportLookupError('You do not have access to that report', 401)

  # If the user doesn't have permission to view this report, show an error message
  if not (report.username == user.name or user_is_admin()):
    raise ReportLookupError('You do not have access to that report', 401)
