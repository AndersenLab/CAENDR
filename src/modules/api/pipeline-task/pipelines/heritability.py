import os
import logging
import tabix

from caendr.models.task import HeritabilityTask
from caendr.models.datastore import HeritabilityReport
from caendr.services.heritability_report import get_heritability_report
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE = os.environ.get('GOOGLE_CLOUD_ZONE')

MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')


sa_email = f"{MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME}'


SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MACHINE_TYPE = 'n1-standard-1'
PREEMPTIBLE = False
ZONE = 'us-central1-a'
TIMEOUT = '9000s'
BOOT_IMAGE = 'projects/cos-cloud/global/images/family/cos-stable'
VOLUME_NAME = 'nf-pipeline-work'
LOCAL_WORK_PATH = '/workdir'
BOOT_DISK_SIZE_GB = 10
ENABLE_STACKDRIVER_MONITORING = True

COMMANDS = ['python', '/h2/main.py']


def start_heritability_pipeline(task: HeritabilityTask):
  pipeline_req = _generate_heritability_pipeline_req(task)
  return start_pipeline(pipeline_req)


def _generate_heritability_pipeline_req(task: HeritabilityTask):
  h = HeritabilityReport(task.id)
  
  image_uri = f"{task.container_repo}/{task.container_name}:{task.container_version}"
  
  container_name = f"heritability-{h.id}"
  environment = {"DATA_HASH": h.data_hash, 
                 "DATA_BUCKET": h.get_bucket_name(), 
                 "DATA_BLOB_PATH": h.get_blob_path()}

  service_account = ServiceAccount(email=sa_email, scopes=SCOPES)
  virtual_machine = VirtualMachine(machine_type=MACHINE_TYPE,
                                  preemptible=PREEMPTIBLE,
                                  boot_disk_size_gb=BOOT_DISK_SIZE_GB,
                                  boot_image=BOOT_IMAGE, enable_stackdriver_monitoring=ENABLE_STACKDRIVER_MONITORING, service_account=service_account)
  resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])
  action = Action(always_run=False, block_external_network=False, commands=COMMANDS, container_name=container_name, disable_image_prefetch=False,
                  disable_standard_error_capture=False, enable_fuse=False, environment=environment, ignore_exit_status=False, image_uri=image_uri, 
                  publish_exposed_ports=False, run_in_background=False, timeout=TIMEOUT)
  pipeline = Pipeline(actions=[action], resources=resources, timeout=TIMEOUT)
  pipeline_req = Request(pipeline=pipeline, pub_sub_topic=pub_sub_topic)
  return pipeline_req
