locals {
  dockerfile_path = abspath("${path.module}/../../../../src/modules/site-v2")
}

data "google_container_registry_image" "module_site" {
  name = var.module_site_vars.container_name
  tag = var.module_site_vars.container_version
}


resource "null_resource" "build_container_module_site" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_site.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s container-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }
}

resource "null_resource" "publish_container_module_site" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.module_site.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s publish-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }

  depends_on = [
    null_resource.build_container_module_site
  ]
}

resource "time_sleep" "wait_publish_container_module_site" {
  create_duration = "30s"

  depends_on = [
    null_resource.publish_container_module_site
  ]
}
