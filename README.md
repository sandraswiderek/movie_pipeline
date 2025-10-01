# Movie Pipeline

This project builds a serverless data pipeline for movie box office analysis. It ingests movie revenue CSVs and enriches them with OMDb API data. Then it models the data in BigQuery and powers an interactive Power BI dashboard.

### Technologies
- 🗂️ Cloud Storage
- ⚡ Cloud Run
- 🗄️ BigQuery
- 🧩 Dataform
- 🌍 Terraform
- ⏱️ Cloud Scheduler
- 🐍 Python
- 💾 SQL
- 📊 Power BI

----------
## 🎯 Project Goal
Analyze movie box office performance by building a serverless pipeline.

----------

## 📊 Pipeline Flow
```[CSV in Cloud Storage] → [Cloud Run (clean + hash)] → [BigQuery staging table] → [BigQuery revenues table] → [Cloud Run (OMDb enrichment)] → [movie details table] → [Dataform (joined + materialized views)] → [Power BI]```

----------

## 📐 Architecture
This pipeline is built on a serverless, event-driven architecture using Google Cloud services.

### Workflow:

### Data Ingestion 📥
- User uploads a CSV file to Cloud Storage.
- This event triggers a Cloud Run Job to clean the file (quotes, semicolons), add a title hash, and save it into a processed bucket.
- Data is loaded into a BigQuery staging table, validated, and merged into the main table.

### Enrichment 🔑
- A scheduled Cloud Run Job calls the OMDb API.
- It checks which ```title_hash``` values from the main fact table that are not already enriched.
- For those titles, it retrieves attributes (genre, director, actors, ratings, box office, etc.).
- The results are stored in a separate movie details table in BigQuery.
- ⚠️ No new movies are added – only titles that already exist in the CSV data are enriched.
- 🔄 API Limit: the free OMDb API key allows only 1,000 queries per day, so the job processes up to 900 daily to stay under the limit.

### Modeling 🧩
- Dataform creates a joined view between the revenues table and the movie details table.
- From this, five materialized views are generated:
```fact_daily_revenue```
```dim_movie```
```dim_time```
```dim_genre```
```dim_genre_name```.

### Analytics & Dashboard 📊
- Power BI connects to the BigQuery materialized views.
- Provides interactive dashboards with KPIs, revenue trends, and genre movies comparisons.

--------
## ⚙️ Terraform & GitHub Actions
Infrastructure and deployment are automated.

- Terraform
  - Manages Google Cloud Storage buckets for raw and processed CSVs.
  - Creates BigQuery dataset.

- GitHub Actions️
  - Runs Terraform in CI/CD pipelines for infrastructure provisioning.
  - Deploy new versions of CSV ingesting Cloud Function, enrichment Cloud Run Job and sets up automated schedule in Cloud Scheduler for enrichment job.

--------

## 🧩 Data Model
The schema is a star model:
- ```fact table```: daily revenues per movie per date.
- ```dim_movie```: movie details from OMDb API (boxoffice, ratings, etc.).
- ```dim_time```: calendar attributes (date, month, year).
- ```dim_genre```: movie genres by id.
- ```dim_genre_names```: movie genres by name.

### Comment:
Dimension ```dim_genre``` handled in SQL instead of  Python – it could have been generated stable ```genre_id``` directly in the preprocessing script and skipped ```dim_genre``` in the warehouse. That would remove one extra table. I chose to keep ```dim_genre``` for simplicity and avoid adding more logic to the ingestion code.

### ER diagram
<img width="1513" height="586" alt="image" src="https://github.com/user-attachments/assets/e96586f4-9eb4-4664-8d63-f8c7ac211999" />


--------

## Dashboard Demo
### Power BI Dashboard (click to see): [XXX]
Example screenshot:
<img width="1221" height="693" alt="image" src="https://github.com/user-attachments/assets/323ea341-0920-41f0-a2de-2322aecab541" />

-------

## Other possible methods
- Cloud Functions instead of Cloud Run – simpler and cheaper, but only good for very small tasks. Cloud Run fits better here because it handles longer jobs and batching.
- Dataflow instead of Cloud Run – powerful for large or streaming pipelines, but overkill for small CSV batches. Cloud Run is lighter and cheaper.
- Cloud Composer instead of Scheduler – great for complex workflows, but too heavy and costly. Scheduler is enough for a two-job pipeline.
- dbt instead of Dataform – big ecosystem and testing features, but requires extra setup. Dataform is native in BigQuery and easier to use.
- Python transforms instead of BigQuery (ELT) – flexible but harder to maintain. BigQuery SQL transformations are scalable and simple.
- Looker Studio instead of Power BI – free and native to GCP, but the free version is limited in complex visuals. Power BI offers richer, more advanced visualizations.

---------

### Future Improvements
- adding more dimensions such as ```dim_actors```, ```dim_director```, ```dim_language```, ```dim_country``` for deeper analytics






