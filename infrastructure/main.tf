resource "google_storage_bucket" "input_bucket" {
  name                        = var.input_bucket
  location                    = var.location
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "staging_bucket" {
  name                        = var.staging_bucket
  location                    = var.location
  uniform_bucket_level_access = true
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id  = var.dataset_id
  location    = var.location
}
