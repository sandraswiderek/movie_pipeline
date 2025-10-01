PROJECT_ID=data-warehouse-473119
PROJECT_NUM=542527165512
REGION=europe-central2
TF_STATE_BUCKET=terraform_data_warehouse_state_bucket
CI_SA_NAME=github
CI_SA="$CI_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
GCS_SA="service-$PROJECT_NUM@gs-project-accounts.iam.gserviceaccount.com"

# creates service account used during deployment of Cloud Run resources
gcloud iam service-accounts create $CI_SA_NAME \
  --display-name=$CI_SA

gcloud iam service-accounts keys create ./github-key.json \
  --iam-account=$CI_SA

# enabled google cloud APIs
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  bigquery.googleapis.com \
  bigquerystorage.googleapis.com \
  bigqueryconnection.googleapis.com \
  cloudscheduler.googleapis.com \
  --project "$PROJECT_ID"

# assigns roles to previously created service account
for role in \
  roles/editor \
  roles/cloudfunctions.admin \
  roles/run.admin \
  roles/eventarc.admin \
  roles/pubsub.publisher \
  roles/artifactregistry.writer
do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CI_SA" \
  --role="$role"
done

# creates bucket for Terraform state
gcloud storage buckets create gs://$TF_STATE_BUCKET \
  --project=$PROJECT_ID \
  --location=$REGION \
  --uniform-bucket-level-access

# create GCS identity if does not exists
gcloud beta services identity create \
  --service=storage.googleapis.com \
  --project="$PROJECT_ID"

# assign role to default GCS service account. It allows to publish events to Pub/Sub
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GCS_SA" \
  --role="roles/pubsub.publisher"
