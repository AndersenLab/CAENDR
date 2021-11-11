module "img_thumb_gen" {
  source = "./modules/img-thumb-gen"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_img_thumb_gen_vars = local.module_img_thumb_gen_vars
  
  depends_on = [
    null_resource.api_service_group_all
  ]
}


module "static" {
  source = "./modules/static"
  ENVIRONMENT = var.ENVIRONMENT

  module_static_vars = local.module_static_vars
  google_cloud_vars = local.google_cloud_vars

  asset_versioning = true

  depends_on = [
    module.site
  ]
}



module "site" {
  source = "./modules/site"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_site_vars = local.module_site_vars
  cloud_secret_vars = local.cloud_secret_vars

  depends_on = [
    null_resource.api_service_group_all
  ]
}

