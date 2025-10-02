
from google.cloud.exceptions import NotFound
from google.cloud import bigquery
import requests
import time
import os
import sys
import json

PROJECT_ID   = os.getenv("PROJECT_ID")
LOCATION     =  os.getenv('LOCATION')
BQ_DATASET   = os.getenv('DATASET')
BQ_TABLE     = os.getenv('BASE_TABLE')
BQ_TABLE_ENRICHED     = os.getenv('ENRICHED_TABLE')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
SLEEP_BETWEEN_CALLS = 0.3
MAX_QUERIES   = int(os.getenv("MAX_QUERIES"))

def job():
    """Read titles that are not yet enriched, call the OMDb API, and insert enriched rows into BigQuery."""
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    enriched_table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_ENRICHED}"

    # Ensure the enriched table exists, create it if it does not
    try:
        client.get_table(enriched_table_id)
    except NotFound:
        schema = [
            bigquery.SchemaField("title_hash", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("genre", "STRING"),
            bigquery.SchemaField("director", "STRING"),
            bigquery.SchemaField("actors", "STRING"),
            bigquery.SchemaField("writer", "STRING"),
            bigquery.SchemaField("country", "STRING"),
            bigquery.SchemaField("language", "STRING"),
            bigquery.SchemaField("boxoffice", "STRING"),
            bigquery.SchemaField("ratings_internetmoviedatabase", "STRING"),
            bigquery.SchemaField("ratings_rottentomatoes", "STRING"),
            bigquery.SchemaField("ratings_metacritic", "STRING"),
        ]
        client.create_table(bigquery.Table(enriched_table_id, schema=schema))

    # Select titles that are not yet present in the enriched table. Randomize (sample) so we don’t always hit the same titles first.
    # The titles sample is randomised in Cloud Function but order randomization might be done by BigQuery as well - probably better approach long-term.
    to_process = client.query_and_wait(f"""
        SELECT DISTINCT title_hash, title
        FROM `{table_id}`
        EXCEPT DISTINCT
        SELECT DISTINCT title_hash, title
        FROM `{enriched_table_id}`;
    """).to_dataframe().sample(frac=1)

    
    print(f"movies to process: {len(to_process.index)}")

    
    n = 0
    # OMDb API is called at most MAX_QUERIES times. 
    # The better approach (but more complicated) might be to additionally add API limit exceeding detection -
    # in this case loop would be able to exit sooner without overflowing API with unnecessary requests.
    for row in to_process.itertuples(index=False):
        if n >= MAX_QUERIES:
            break
        n += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        title_hash = row.title_hash
        title = row.title


        # Call OMDb
        try:
            r = requests.get("https://www.omdbapi.com/", params={"apikey": OMDB_API_KEY, "t": title, "plot": "short"}, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("Response") != "True":
                print(f"failed to get data for movie {title}: {data}")
                continue
        except Exception as e:
            print(f"failed to get data for movie {title}: {e}")
            continue
    

        # Normalize keys to lowercase, expand ratings into flat columns
        data = { (k.lower() if isinstance(k, str) else k): v for k, v in data.items() }
        for idx, item in enumerate(data["ratings"], start=1):
            src = item.get("Source")
            val = item.get("Value")
            if src:
                data[f"ratings_{src.replace(' ', '').replace('-', '').lower()}"] = val

    
        row_dict = {c.lower(): v for c, v in zip(to_process.columns, row)}
        enriched = {**row_dict, **data}
        
        # Insert into BigQuery
        errors = client.insert_rows_json(enriched_table_id, [enriched], skip_invalid_rows=False, ignore_unknown_values=True)
        if errors:
            print(f"failed to insert enriched data for movie {title}: {errors}")


if __name__ == "__main__":
    try:
        job()
    except Exception as err:
        message = (
            f"Task failed: {str(err)}"
        )

        print(json.dumps({"message": message, "severity": "ERROR"}))
        sys.exit(1)