locals {
  dockerfile_path = abspath("${path.module}/../../../../src/modules/site")
}

data "google_container_registry_image" "module_site" {
  name = var.module_site_vars.container_name
  tag = var.module_site_vars.container_version
}


resource "null_resource" "build_container_module_site" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_site.image_url,
    "container_digest" = data.google_container_registry_image.module_site.digest
  })

  provisioner "local-exec" {
    command = format("make -C %s container-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }
}

resource "null_resource" "publish_container_module_site" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_site.image_url,
    "container_digest" = data.google_container_registry_image.module_site.digest
  })

  provisioner "local-exec" {
    command = format("make -C %s publish-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }

  depends_on = [
    null_resource.build_container_module_site
  ]
}

resource "time_sleep" "wait_container_publish_db_ops" {
  create_duration = "120s"

  depends_on = [
    null_resource.publish_container_module_site
  ]
}
