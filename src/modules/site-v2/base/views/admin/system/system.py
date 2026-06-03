from flask import (render_template,
                    Blueprint)
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Iterable

from google.cloud import compute_v1
import os

# Tools blueprint
admin_system_bp = Blueprint('system',
                      __name__,
                      template_folder='templates')




def list_all_instances(
    project_id: str,
) -> Dict[str, Iterable[compute_v1.Instance]]:
    """
    Returns a dictionary of all instances present in a project, grouped by their zone.

    Args:
        project_id: project ID or project number of the Cloud project you want to use.
    Returns:
        A dictionary with zone names as keys (in form of "zones/{zone_name}") and
        iterable collections of Instance objects as values.
    """
    instance_client = compute_v1.InstancesClient()
    request = compute_v1.AggregatedListInstancesRequest()
    request.project = project_id
    # Use the `max_results` parameter to limit the number of results that the API returns per response page.
    request.max_results = 50

    agg_list = instance_client.aggregated_list(request=request)

    all_instances = defaultdict(list)
    print("Instances found:")
    # Despite using the `max_results` parameter, you don't need to handle the pagination
    # yourself. The returned `AggregatedListPager` object handles pagination
    # automatically, returning separated pages as you iterate over the results.
    for zone, response in agg_list:
        if response.instances:
            all_instances[zone].extend(response.instances)
            print(f" {zone}:")
            for instance in response.instances:
                print(f" - {instance.name} ({instance.machine_type})")
    return all_instances


def _get_instances():
  project_id = os.getenv('GOOGLE_CLOUD_PROJECT_NUMBER')
  return list_all_instances(project_id)  


@admin_system_bp.route('/')
def system_dashboard():
  disable_parent_breadcrumb = True
  instances = _get_instances()
  now = datetime.today()

  module_name = os.getenv("MODULE_NAME", "n/a")
  module_version = os.getenv("MODULE_VERSION", "n/a")
  git_commit = os.getenv("GIT_COMMIT", "n/a")


  return render_template('admin/system/system.html', **locals())

