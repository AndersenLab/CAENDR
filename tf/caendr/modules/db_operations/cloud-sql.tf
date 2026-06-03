resource "google_sql_database" "postgres_db_main" {
  charset   = "UTF8"
  collation = "en_US.UTF8"
  instance  = google_sql_database_instance.postgres_instance.name
  name      = var.module_db_operations_vars.postgres_db_name
  project   = var.google_cloud_vars.project_id
}

resource "google_sql_database" "postgres_db_stage" {
  charset   = "UTF8"
  collation = "en_US.UTF8"
  instance  = google_sql_database_instance.postgres_instance.name
  name      = var.module_db_operations_vars.postgres_db_stage_name
  project   = var.google_cloud_vars.project_id
}

resource "google_sql_database_instance" "postgres_instance" {
  database_version = "POSTGRES_13"
  name             = var.module_db_operations_vars.postgres_instance_name
  project          = var.google_cloud_vars.project_id
  region           = var.google_cloud_vars.region

  deletion_protection = false

  settings {
    activation_policy = "ALWAYS"
    availability_type = "ZONAL"

    backup_configuration {
      backup_retention_settings {
        retained_backups = "5"
        retention_unit   = "COUNT"
      }

      binary_log_enabled             = "false"
      enabled                        = "false"
      location                       = "us"
      point_in_time_recovery_enabled = "false"
      start_time                     = "05:00"
      transaction_log_retention_days = "7"
    }

    disk_autoresize        = "false"
    disk_autoresize_limit  = "0"
    disk_size              = "10"
    disk_type              = "PD_SSD"

    insights_config {
      query_insights_enabled  = "true"
      query_string_length     = "1024"
      record_application_tags = "false"
      record_client_address   = "false"
    }

    ip_configuration {
      ipv4_enabled = "true"
      require_ssl  = "false"
      
      # authorized_networks {
      #   name  = "sam"
      #   value = "73.247.119.202"
      # }
    }

    location_preference {
      zone = "us-central1-a"
    }

    maintenance_window {
      day  = "3"
      hour = "5"
    }

    pricing_plan     = "PER_USE"
    # tier             = "db-g1-small"
    # tier             = "db-custom-1-3840"
    tier             = "db-custom-2-7680"
  }
}

resource "google_sql_user" "users" {
  name     = var.module_db_operations_vars.postgres_db_user_name
  instance = google_sql_database_instance.postgres_instance.name
  password = var.module_db_operations_vars.postgres_db_password
}