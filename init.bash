PROJECT_ID=data-warehouse-473119
LOCATION=EU
TF_STATE_BUCKET=state_bucket_sandi
CI_SA=github@${PROJECT_ID}.iam.gserviceaccount.com
RUNTIME_SA=${PROJECT_ID}@appspot.gserviceaccount.com 

gcloud storage buckets create gs://${TF_STATE_BUCKET} \
  --project=${PROJECT_ID} \
  --location=${LOCATION} \
  --uniform-bucket-level-access

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
  --project "$PROJECT_ID"

for role in \
  roles/cloudfunctions.admin \
  roles/run.admin \
  roles/eventarc.admin \
  roles/pubsub.admin \
  roles/artifactregistry.writer
do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CI_SA}" --role="$role"
done

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:${CI_SA}" \
  --role="roles/iam.serviceAccountUser"
