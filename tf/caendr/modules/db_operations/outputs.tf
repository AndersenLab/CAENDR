output "db_connection_uri" {
  value = google_sql_database_instance.postgres_instance.connection_name
}
