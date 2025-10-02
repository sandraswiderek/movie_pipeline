import pandas as pd
import hashlib
from google.cloud import storage, bigquery
from cloudevents.http import CloudEvent
import os
import time 
from google.cloud.exceptions import NotFound

PROJECT_ID   = os.getenv('PROJECT_ID')
LOCATION     =  os.getenv('LOCATION') 
BUCKET_NAME  =  os.getenv('TEMP_BUCKET') 
BQ_DATASET   = os.getenv('DEST_DATASET') 
BQ_TABLE     =  os.getenv('DEST_TABLE')  


def fix_line(line: str) -> str:
    line = line.rstrip("\r\n")
    if line.endswith(";"):
        line = line[:-1]
    line = line.replace("\"\"", "\"")
    if line[0] == "\"" and line[-1] == "\"": line = line[1:-1]
    return line + "\n"

def triggering_bucket(event: CloudEvent):
    """
    Runs when a file appears in GCS.
    Steps:
    1) Download CSV.
    2) Clean it and add `title_hash`.
    3) Upload cleaned file to a temp bucket.
    4) Load to BigQuery.
       - First time: load straight to target table.
       - Next times: load to staging and MERGE into target.
    """
    data = event.data
    print(event)
    bucket_name = data["bucket"]
    file_name = data["name"]

    input_gs_uri = f"gs://{bucket_name}/{file_name}"


    # Download original CSV
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.download_to_filename("temp.csv")

    # Clean CSV
    with open("temp.csv", "r", encoding="utf-8-sig", newline="") as fin, \
        open("temp-fixed.csv", "w", encoding="utf-8", newline="\n") as fout:
        for raw in fin:
            fout.write(fix_line(raw))

    # Add a stable hash for title
    df = pd.read_csv("temp-fixed.csv", engine="python")
    titles = df["title"].astype(str).str.strip()
    df["title_hash"] = titles.map(lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest())
    df.to_csv("temp-final.csv", index=False)

    # Upload cleaned file to staging bucket
    dest_blob = f"temp-{int(time.time() * 1000)}-{file_name.replace(' ', '').replace('-', '').lower()}"
    print(f"dest_blob: {dest_blob}")
    bucket = gcs_client.bucket(BUCKET_NAME)
    blob = bucket.blob(dest_blob)

   
    blob.upload_from_filename("temp-final.csv", content_type="text/csv")
    gs_uri = f"gs://{BUCKET_NAME}/{dest_blob}"
    print("Uploaded to:", gs_uri)


    # Load to BigQuery
    bq = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    stg_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}-staging"
    tgt_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,          
        autodetect=True,         
        field_delimiter=",",
        allow_quoted_newlines=True,   
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, 
    )


    # If target exists -> use staging + MERGE, else load to target
    merge = True
    job_config_table = stg_id
    try:
        bq.get_table(tgt_id)
    except NotFound:
        merge = False
        job_config_table = tgt_id


    print(gs_uri)
    load_job = bq.load_table_from_uri(
        gs_uri,
        job_config_table,
        job_config=job_config,
        location=LOCATION, 
    )

    print("Starting load job:", load_job.job_id)
    result = load_job.result() 
    print("Load job finished.")
    if merge == False:
        # First load: nothing to merge
        return


    # Merge new rows into target (insert only; add UPDATE if needed)
    merge_sql = f"""
    MERGE `{tgt_id}` T
    USING (
      SELECT * FROM `{stg_id}`
    ) S
    ON T.id = S.id
    WHEN NOT MATCHED THEN
      INSERT ROW
    """

    bq.query(merge_sql, location=LOCATION).result()

    print(f"Merged {gs_uri} into {tgt_id} without duplicate ids.")

    
    table = bq.get_table(tgt_id)
    print(f"Loaded {table.num_rows} rows into {table.full_table_id}.")
    print("Schema:")
    for f in table.schema:
        print(f" - {f.name}: {f.field_type} (mode={f.mode})")


