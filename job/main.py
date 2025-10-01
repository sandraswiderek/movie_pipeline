
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
    #table_id to tabela z danymi z csv + hash, a enriched_table_id to same dane z api
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    enriched_table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_ENRICHED}"

    #bierzemy tabelę enriched, no chyba, że jej nie ma to ją tworzymy
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

    #te rows które nie zostały jeszcze przeprocesowane dodajemy do dataframe, 'sample' bo brane title i title_hash muszą być losowe, 
    # bo za każdym razem gdybysmy odpalali query to pierwsze rows ciągle byłyby te same i ciągle by się nawarstwiały na początku
    to_process = client.query_and_wait(f"""
        SELECT DISTINCT title_hash, title
        FROM `{table_id}`
        EXCEPT DISTINCT
        SELECT DISTINCT title_hash, title
        FROM `{enriched_table_id}`;
    """).to_dataframe().sample(frac=1)

    #ile jeszcze tytułów trzeba przeprocesować
    print(f"movies to process: {len(to_process.index)}")

    #pętla procesowania rows, funckja sleep aby chociaz lekko opoznic pomiędzy zapytaniami, zeby za szybko sie nie robiło
    n = 0
    for row in to_process.itertuples(index=False):
        if n >= MAX_QUERIES:
            break
        n += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        title_hash = row.title_hash
        title = row.title

    #robie zapytanie do api, w ciagu 15 sekund mam otrzymac inf zwrotną jak nie dostane to sie przerywa i leci z kolejnym row; 
    # raise_for stat - jezeli otrzymam status z bledem np 500 to dostane błąd; jezeli dostane error to zwroci mi np: {"Response":"False","Error":"Movie not found!"}
    # i leci z kolejnym row
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
    # jezeli bedzie error ogolnie z innego powodu w try, to dostane exception i wypisze mi ten błąd ('e')

    #jeżeli key jest stringiem, konwerujemy na małe litery, w przeciwnym razie zostawiamy, w ratings są zagnieżdzone dane bo są w dict, definiuje się nazwę
    # skąd jest rating i jego value, source zamieniamy na nazwe aby wiedziec skad rating poprzez 'rating_' + nazwa source bez spacji i bez -, z małych liter
        data = { (k.lower() if isinstance(k, str) else k): v for k, v in data.items() }
        for idx, item in enumerate(data["ratings"], start=1):
            src = item.get("Source")
            val = item.get("Value")
            if src:
                data[f"ratings_{src.replace(' ', '').replace('-', '').lower()}"] = val

    #o co chodzi w zip? enriched czyli łączyli title+title_hash z columnami z api, wysyłane jest zapytanie do bq - jezeli dodane dane do enriched table są w 
    # np. złym formacie to dostajemy komunikat
        row_dict = {c.lower(): v for c, v in zip(to_process.columns, row)}
        enriched = {**row_dict, **data}
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
        sys.exit(1)  # Retry Job Task by exiting the process