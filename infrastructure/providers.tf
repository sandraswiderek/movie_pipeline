provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = var.credentials_json != "" ? var.credentials_json : null
}
