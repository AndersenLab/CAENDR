module "img_thumb_gen" {
  source = "./modules/img_thumb_gen"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  bucket_photos_name = var.MODULE_SITE_BUCKET_PHOTOS_NAME
  image_source_path = var.MODULE_IMG_THUMB_GEN_SOURCE_PATH
  
  depends_on = [
    null_resource.api_service_group_all
  ]
}

module "db_operations" {
  source = "./modules/db_operations"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_db_operations_vars = local.module_db_operations_vars
  
  depends_on = [
    null_resource.api_service_group_all
  ]
}

module "gene_browser_tracks" {
  source = "./modules/gene_browser_tracks"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_gene_browser_tracks_vars = local.module_gene_browser_tracks_vars
  
  depends_on = [
    null_resource.api_service_group_all
  ]
}


module "api_pipeline_task" {
  source = "./modules/api/pipeline_task"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_api_pipeline_task_vars = local.module_api_pipeline_task_vars

  depends_on = [
    null_resource.api_service_group_all
  ]
}



module "ext_assets" {
  source = "./modules/ext_assets"
  ENVIRONMENT = var.ENVIRONMENT

  bucket_assets_name = var.MODULE_SITE_BUCKET_ASSETS_NAME
  google_cloud_vars = local.google_cloud_vars

  asset_versioning = true

  depends_on = [
    null_resource.api_service_group_all
  ]
}



module "site" {
  source = "./modules/site"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_site_vars = local.module_site_vars
  cloud_secret_vars = local.cloud_secret_vars

  cloud_sql_connection_uri = module.db_operations.db_connection_uri
  api_pipeline_task_url = module.api_pipeline_task.url

  depends_on = [
    module.gene_browser_tracks,
    module.ext_assets,
    module.img_thumb_gen,
    null_resource.api_service_group_all
  ]
}

