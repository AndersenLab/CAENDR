locals {
  dockerfile_path = abspath("${path.module}/../../../../../../../../../src/modules/gene_browser_tracks")
}

data "google_container_registry_image" "gene_browser_tracks" {
  name = var.module_gene_browser_tracks_vars.container_name
  tag = var.module_gene_browser_tracks_vars.container_version
}

resource "null_resource" "build_container_gene_browser_tracks" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.gene_browser_tracks.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s container-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }
}

resource "null_resource" "publish_container_gene_browser_tracks" {
  triggers = tomap({
    "container_url" = data.google_container_registry_image.gene_browser_tracks.image_url
  })

  provisioner "local-exec" {
    command = format("make -C %s publish-auto ENV=%s", local.dockerfile_path, var.ENVIRONMENT)
  }

  depends_on = [
    null_resource.build_container_gene_browser_tracks
  ]
}

resource "time_sleep" "wait_publish_container_gene_browser_tracks" {
  create_duration = "120s"

  depends_on = [
    null_resource.publish_container_gene_browser_tracks
  ]
}
