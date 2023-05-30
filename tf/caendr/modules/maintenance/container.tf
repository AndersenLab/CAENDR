locals {
  dockerfile_path = abspath("${path.module}/../../../../src/modules/maintenance")
}

data "google_container_registry_image" "module_maintenance" {
  name = var.module_maintenance_vars.container_name
  tag = var.module_maintenance_vars.container_version
}


resource "null_resource" "build_container_module_maintenance" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_maintenance.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s container-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }
}

resource "null_resource" "publish_container_module_maintenance" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_maintenance.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s publish-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }

  depends_on = [
    null_resource.build_container_module_maintenance
  ]
}

resource "time_sleep" "wait_publish_container_module_maintenance" {
  create_duration = "30s"

  depends_on = [
    null_resource.publish_container_module_maintenance
  ]
}
