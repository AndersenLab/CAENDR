resource "google_service_account" "sheets_sa" {
  account_id   = var.google_cloud_vars.google_sheets_sa_name
  display_name = "Google Sheets Service Account"
}

resource "google_service_account_key" "sheets_sa" {
  service_account_id = google_service_account.sheets_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "google_service_account" "analytics_sa" {
  account_id   = var.google_cloud_vars.google_analytics_sa_name
  display_name = "Google Analytics Service Account"
}

resource "google_service_account_key" "analytics_sa" {
  service_account_id = google_service_account.sheets_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

