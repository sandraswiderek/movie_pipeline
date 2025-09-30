provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = var.credentials_json != "" ? var.credentials_json : null
  # If credentials_json is empty, provider will use GOOGLE_CREDENTIALS or
  # Application Default Credentials from the environment.
}
