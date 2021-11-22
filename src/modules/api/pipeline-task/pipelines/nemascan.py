import os
import logging

from caendr.services.cloud.lifesciences import gls_service, ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
NSCALC_REPORT_BUCKET_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_REPORT_BUCKET_NAME')
NSCALC_WORK_BUCKET_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME')
MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')

GOOGLE_CLOUD_PARENT_ID = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"
NSCALC_SERVICE_ACCOUNT = f"{MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"

DS_KIND = 'ns_calc'

IMAGE_URI = 'andersenlab/nemascan-nxf:1.0'
PUB_SUB_TOPIC = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME}'

SCOPE = "https://www.googleapis.com/auth/cloud-platform"

MACHINE_TYPE = 'n1-standard-1'
PREEMPTIBLE = False
ZONE = 'us-central1-a'
TIMEOUT = '86400s'
BOOT_IMAGE = 'projects/cos-cloud/global/images/family/cos-stable'

NS_DATA_PATH = f'gs://{NSCALC_REPORT_BUCKET_NAME}/reports/nemascan'
NS_WORK_PATH = f'gs://{NSCALC_WORK_BUCKET_NAME}/workdir'

VOLUME_NAME = 'nf-pipeline-work'
LOCAL_WORK_PATH = '/workdir'
BOOT_DISK_SIZE_GB = 100
ENABLE_STACKDRIVER_MONITORING = True

COMMAND = 'nemascan-nxf.sh'

class ns_calc_ds:
  def __init__(self, created_on, data_hash, label, modified_on, report_path, status, status_msg, trait, username):
    self.created_on = created_on
    self.data_hash = data_hash
    self.label = label
    self.modified_on = modified_on
    self.report_path = report_path
    self.status = status
    self.status_msg = status_msg
    self.trait = trait
    self.username = username

def start_nemascan_pipeline(data_hash, ds_id):
  pipeline = _generate_nemascan_pipeline_req(data_hash, ds_id)
  run_pipeline_request_body = get_json_from_class(pipeline)
  logging.info(f'NEMASCAN PIPELINE REQUEST: {run_pipeline_request_body}')

  try:
    request = gls_service.projects().locations().pipelines().run(parent=GOOGLE_CLOUD_PARENT_ID, body=run_pipeline_request_body)
    response = request.execute()
    logging.info(f'NEMASCAN PIPELINE: {run_pipeline_request_body}')
    return response
  except Exception as err:
    logging.error(f'start_nemascan_pipeline ERROR: {err}')


def _generate_nemascan_pipeline_req(data_hash, ds_id):
  trait_file = f'{NS_DATA_PATH}/{data_hash}/data.tsv'
  output_dir = f'{NS_DATA_PATH}/{data_hash}/results'
  work_dir = f'{NS_WORK_PATH}/{data_hash}/results'
  container_name = f'nemascan-{ds_id}'
  environment = {'TRAIT_FILE': trait_file, 'OUTPUT_DIR': output_dir, 'WORK_DIR': work_dir}

  service_account = ServiceAccount(email=NSCALC_SERVICE_ACCOUNT, scopes=[SCOPE])
  virtual_machine = VirtualMachine(machine_type=MACHINE_TYPE, preemptible=PREEMPTIBLE, boot_disk_size_gb=BOOT_DISK_SIZE_GB, 
                                  boot_image=BOOT_IMAGE, enable_stackdriver_monitoring=ENABLE_STACKDRIVER_MONITORING, service_account=service_account)
  resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])
  action = Action(always_run=False, block_external_network=False, commands=[COMMAND], container_name=container_name, disable_image_prefetch=False,
                  disable_standard_error_capture=False, enable_fuse=False, environment=environment, ignore_exit_status=False, image_uri=IMAGE_URI, 
                  publish_exposed_ports=False, run_in_background=False, timeout=TIMEOUT)
  pipeline = Pipeline(actions=[action], resources=resources, timeout=TIMEOUT)
  pipeline_req = Request(pipeline=pipeline, pub_sub_topic=PUB_SUB_TOPIC)
  return pipeline_req
