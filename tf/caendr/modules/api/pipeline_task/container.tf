locals {
  dockerfile_path = abspath("${path.module}/../../../../../../../../../../src/modules/api/pipeline-task")
}

data "google_container_registry_image" "api_pipeline_task" {
  name = var.module_api_pipeline_task_vars.container_name
  tag = var.module_api_pipeline_task_vars.container_version
}

resource "null_resource" "build_container_api_pipeline_task" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.api_pipeline_task.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s container-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }
}

resource "null_resource" "publish_container_api_pipeline_task" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.api_pipeline_task.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s publish-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }

  depends_on = [
    null_resource.build_container_api_pipeline_task
  ]
}

resource "time_sleep" "wait_container_publish_api_pipeline_task" {
  create_duration = "120s"

  depends_on = [
    null_resource.publish_container_api_pipeline_task
  ]
}


