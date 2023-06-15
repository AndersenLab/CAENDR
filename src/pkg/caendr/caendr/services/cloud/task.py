import os
import json
import datetime

from caendr.services.logger import logger
from flask import request
from google.cloud import tasks_v2

from caendr.models.error import APIBadRequestError, DuplicateTaskError
from caendr.services.cloud.datastore import get_ds_entity


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')

taskClient = tasks_v2.CloudTasksClient()


def add_task(queue, url, payload, delay_seconds=None, task_name=None):
  parent = taskClient.queue_path(GOOGLE_CLOUD_PROJECT_ID, GOOGLE_CLOUD_REGION, queue)
  
  task = {
    "http_request": { 
      "http_method": tasks_v2.HttpMethod.POST,
      "url": url,
    }
  }

  if payload is not None:
    if isinstance(payload, dict):
      payload = json.dumps(payload)
      task["http_request"]["headers"] = {"Content-type": "application/json"}

    converted_payload = payload.encode()
    task["http_request"]["body"] = converted_payload

  if delay_seconds is not None:
    # Convert "seconds from now" into an rfc3339 datetime string then into a Timestamp protobuf.
    d = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
    schedule_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
    task["schedule_time"] = schedule_time

  if task_name is not None:
    task["name"] = f"{parent}/tasks/{task_name}"

  try:
    response = taskClient.create_task(request={"parent": parent, "task": task})
    logger.debug(f"Created task {response.name}")
  except Exception as e:
    logger.error(f"Failed to create task {e}")
    eType = str(type(e).__name__)
    if eType == 'AlreadyExists':
      raise DuplicateTaskError()
    else:
      response = None
    
  return response



def verify_task_headers(task_route):
  """ Check headers to verify the task name and queue are present and queue is correct """
  task_name = request.headers.get("X-Cloudtasks-Taskname")
  if task_name == None:
    raise APIBadRequestError("Missing X-Cloudtasks-Taskname header")

  queue_name = request.headers.get("X-Cloudtasks-Queuename")
  if queue_name == None:
    raise APIBadRequestError("Missing X-Cloudtasks-Queuename header")
  
  # Route must match task queue name
  if task_route != queue_name:
    raise APIBadRequestError("Task route does not match task queue")

  return queue_name, task_name


def update_task_status(task, status, status_msg=None):
  entity = get_ds_entity(task.ds_kind, task.ds_id)
  data = {'status': status}
  if status_msg is not None:
    data['status_msg'] = status_msg

  # update_ds_entity(entity, data)  

  # TODO: write to ds
