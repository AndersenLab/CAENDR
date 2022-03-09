import os
import logging

from caendr.models.task import DatabaseOperationTask
from caendr.models.datastore import DatabaseOperation
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')

MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')

MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')


sa_email = f"{MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME}'


COMMAND = '/db_operations/run.sh'

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MACHINE_TYPE = 'n1-standard-4'
PREEMPTIBLE = False
ZONE = 'us-central1-a'
TIMEOUT = '86400s'
BOOT_IMAGE = 'projects/cos-cloud/global/images/family/cos-stable'
VOLUME_NAME = 'db_op_work'
LOCAL_WORK_PATH = '/workdir'
BOOT_DISK_SIZE_GB = 50
ENABLE_STACKDRIVER_MONITORING = True


def start_db_op_pipeline(task: DatabaseOperationTask):
  pipeline_req = _generate_db_op_pipeline(task)
  return start_pipeline(pipeline_req)


def _generate_db_op_pipeline(task: DatabaseOperationTask):
  d = DatabaseOperation(task.id)
  image_uri = f"{task.container_repo}/{task.container_name}:{task.container_version}"
  
  container_name = f"db-op-{d.id}"
  environment = task.args
  environment['DATABASE_OPERATION'] = task.db_operation
  environment['USERNAME'] = task.username if task.username else None
  environment['EMAIL'] = task.email if task.email else None
  

  service_account = ServiceAccount(email=sa_email, scopes=SCOPES)
  virtual_machine = VirtualMachine(machine_type=MACHINE_TYPE, preemptible=PREEMPTIBLE, boot_disk_size_gb=BOOT_DISK_SIZE_GB, 
                                  boot_image=BOOT_IMAGE, enable_stackdriver_monitoring=ENABLE_STACKDRIVER_MONITORING, service_account=service_account)
  resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])
  action = Action(always_run=False, block_external_network=False, commands=[COMMAND], container_name=container_name, disable_image_prefetch=False,
                  disable_standard_error_capture=False, enable_fuse=False, environment=environment, ignore_exit_status=False, image_uri=image_uri, 
                  publish_exposed_ports=False, run_in_background=False, timeout=TIMEOUT)
  pipeline = Pipeline(actions=[action], resources=resources, timeout=TIMEOUT)
  pipeline_req = Request(pipeline=pipeline, pub_sub_topic=pub_sub_topic)
  return pipeline_req
