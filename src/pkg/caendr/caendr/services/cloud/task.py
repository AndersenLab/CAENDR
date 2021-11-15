from flask import request

from caendr.models.error import APIBadRequestError
from caendr.services.cloud.datastore import get_ds_entity, update_ds_entity

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

  update_ds_entity(entity, data)  

  # TODO: write to ds

class Task(object):
  def __init__(self, hash, ds_id, ds_kind):
      self.hash = hash
      self.ds_id = ds_id
      self.ds_kind = ds_kind
