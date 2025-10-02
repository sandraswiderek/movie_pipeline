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
- User uploads a CSV file to Cloud Storage ```ingest_input_bucket``` .
- This event triggers a Cloud Function to clean the file (quotes, semicolons), add a title hash, and save it into a ```ingest_staging_bucket```.
- Data is loaded into a BigQuery staging table (starting with the second CSV upload - the first load skips staging), validated, and merged into the ```revenues_per_day``` table.

### Enrichment 🔑
- A scheduled Cloud Run Job calls the OMDb API.
- It checks which ```title_hash``` values from the main fact table that are not already enriched.
- For those titles, it retrieves attributes (ratings, box office, etc.).
- The results are stored in a separate ```movies_enriched``` table in BigQuery.
- ⚠️ No new movies are added – only titles that already exist in the CSV data are enriched.
- 🔄 API Limit: the free OMDb API key allows only 1,000 queries per day, so the job processes up to 900 daily to stay under the limit.

Comment: Execute a fixed number of requests based on an environment variable. A better approach would be to read API responses to detect how many requests have been used. For simplicity I did not implement that. Ideally is to combine two approaches.

### Modeling 🧩
- Dataform creates a joined view between the revenues table and the movie details table.
- From this, five other views are generated:
```fact_daily_revenue```
```dim_movie```
```dim_time```
```dim_genre```
```dim_genre_name```.

Comment: There is a view built on top of another view. That’s acceptable here given the small data volume, but for larger datasets a materialized view would deliver better performance.


### Analytics & Dashboard 📊
- Power BI connects to the BigQuery.
- Provides interactive dashboards box office trends.

--------
## ⚙️ Terraform & GitHub Actions
Infrastructure and deployment are automated.

- Terraform
  - Manages Google Cloud Storage buckets for raw and processed CSVs.
  - Creates BigQuery dataset.

- GitHub Actions️
  - Runs Terraform in CI/CD pipelines.
  - Deploy new versions of CSV ingesting Cloud Function, enrichment Cloud Run Job and sets up automated schedule in Cloud Scheduler for enrichment job.

- ```init.bash```: initializes the service account used later in GitHub Actions.It enables the required APIs, grants the necessary permissions, and creates a bucket for Terraform state.

--------

## 🧩 Data Model
The schema is a star model:
- ```fact table```: daily revenues per movie per date.
- ```dim_movie```: movie details from OMDb API (boxoffice, ratings, etc.).
- ```dim_time```: calendar attributes (date, month, year).
- ```dim_genre```: movie genres by id.
- ```dim_genre_names```: movie genres by name.

### Comment:
The dimension ```dim_genre``` is handled in SQL instead of Python. It could have been generated stable ```genre_id``` directly in the preprocessing script and skipped ```dim_genre``` in the warehouse. That would remove one extra table. I chose to keep ```dim_genre``` for simplicity and avoid adding more logic to the ingestion code.

### ER diagram
<img width="1617" height="607" alt="image" src="https://github.com/user-attachments/assets/57c1e4bb-fe3f-4279-9912-470c783f2891" />


--------

## Dashboard Demo
### Power BI Dashboard (click to see): [![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open-brightgreen)](https://app.powerbi.com/links/5-V3WCrDIm?ctid=ae65f568-0ceb-42c2-9dda-731b9c16e6b4&pbi_source=linkShare)

Example screenshot:
<img width="1227" height="687" alt="image" src="https://github.com/user-attachments/assets/1e57980e-1acb-4380-bccb-5b90c7ce9db8" />

-------

## Other possible methods
- Cloud Function instead of Cloud Run – simpler and cheaper, but only good for very small tasks. Cloud Run fits better here.
- Dataflow instead of Cloud Run – powerful for large or streaming pipelines, but overkill for small CSV batches. Cloud Run is lighter and cheaper.
- Cloud Composer instead of Scheduler – great for complex workflows, but too heavy and costly. Scheduler is enough for a two-job pipeline.
- dbt instead of Dataform – big ecosystem and testing features, but requires extra setup. Dataform is native in BigQuery and easier to use.
- Python transforms instead of BigQuery (ELT) – flexible but harder to maintain. BigQuery SQL transformations are scalable and simple.
- Looker Studio instead of Power BI – free and native to GCP, but the free version is limited in complex visuals. Power BI offers richer, more advanced visualizations.

---------

### Future Improvements
- adding more dimensions such as ```dim_actors```, ```dim_director```, ```dim_language```, ```dim_country``` for deeper analytics








