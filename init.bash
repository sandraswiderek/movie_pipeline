PROJECT_ID=data-warehouse-473119
PROJECT_NUM=542527165512
REGION=europe-central2
TF_STATE_BUCKET=state_bucket_sandi
CI_SA_NAME=github
CI_SA=${CI_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
RUNTIME_SA=${PROJECT_ID}@appspot.gserviceaccount.com 


gcloud iam service-accounts create ${CI_SA} \
  --display-name=${CI_SA}

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member=${CI_SA} \
  --role="roles/editor"

gcloud iam service-accounts keys create ./github-key.json \
  --iam-account=${CI_SA}

gcloud storage buckets create gs://${TF_STATE_BUCKET} \
  --project=${PROJECT_ID} \
  --location=${REGION} \
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



gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:service-${PROJECT_NUM}@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"