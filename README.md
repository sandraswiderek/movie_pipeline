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

## 📊 Pipeline Flow High-Level Overview
```[upload CSV to Cloud Storage] → [Cloud Function (csv fix + staging bucket upload)] → [BigQuery staging table] → [BigQuery revenues table] → [Cloud Run (OMDb enrichment)] → [movie details table] → [Dataform (joined + materialized views)] → [Power BI]```

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
- It checks which movies have not been enriched yet and builds titles list.
- For those titles, it retrieves attributes (ratings, box office, etc.).
- The results are stored in a separate ```movies_enriched``` table in BigQuery.
- ⚠️ Each unique movie defined in revenues table is enriched only once.
- 🔄 API Limit: the free OMDb API key allows only 1,000 queries per day, so the job processes up to 900 daily to stay under the limit.

__Comment__: The job executes a fixed number of requests based on an environment variable. A better approach would be to read API responses to detect when request limit is reached. For simplicity I did not implement that. 
Ideally solution would be to combine those two approaches:
- detection of exceeding request limit allows to finish job ealier to not overflow API with unnecessary requests
- fixed upper limit of requests prevent job from sending requests indefinetely when limit detection fails due to e.g. changes in the API responses

### Modeling 🧩
- Dataform creates a joined view (```combined_view```) between the revenues table and the movie details table.
- From this, five other views are generated:
```fact_daily_revenue```
```dim_movie```
```dim_time```
```dim_genre```
```dim_genre_name```.

__Comments__: 
1) Dataform SQL code transforms data types while creating ```combined_view```. Data transformations could have been handled in Python directly. I chose SQL, because transformations there are more simple.
2) Tables ```revenues_per_day``` and ```movies_enriched``` are join together using INNER JOIN. It could have been handled by LEFT JOIN (`revenues_per_day` as a left table). I chose to use an INNER JOIN to keep the analysis consistent. With a LEFT JOIN all movies (including those without any enriched data) would appear in the dashboard and disturb the aggregations. By using an INNER JOIN, movies that are not yet enriched with data do not end up in the dashboard yet.
3) There is a view built on top of another view. That’s acceptable here given the small data volume, but for larger datasets a materialized view would deliver better performance. 

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

- ```init.bash```: initializes the service account used as actor in GitHub Actions. It enables the required APIs, grants the necessary permissions, and creates a bucket for Terraform state.

--------

## 🧩 Data Model
The schema is a star model:
- ```facts_table```: daily revenues per movie per date.
- ```dim_movie```: movie details from OMDb API (boxoffice, ratings, etc.).
- ```dim_time```: calendar attributes (date, month, year).
- ```dim_genre```: movie genres by id.
- ```dim_genre_names```: movie genres by name.

__Comments__:
The column ```genre_id``` in ```dim_genre``` contains hash values generated directly in SQL based on name of genre. ```genre_id``` should have been assigned in a Python script as stable IDs (e.g., the "action" genre always having ```id=2```. I chose to do it by hash to show that i understand the concept and also to avoid adding more logic to the ingestion code.

### ER diagram
<img width="1612" height="608" alt="image" src="https://github.com/user-attachments/assets/77907512-8679-4701-a7df-80ff4c1d2d1e" />


--------

## Dashboard Demo
### Power BI Dashboard (click to see): [![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open-brightgreen)](https://app.powerbi.com/view?r=eyJrIjoiZjgwYjkzYWMtNjgyYS00YjI4LTlmYzEtMzE4YWIwZGQ5ZDA2IiwidCI6ImJhYmFmMzMzLTA5NjQtNGJhYy05ZjNjLWE1NjBjMDNiZTU4MiJ9)

Example screenshot:
<img width="1227" height="687" alt="image" src="https://github.com/user-attachments/assets/1e57980e-1acb-4380-bccb-5b90c7ce9db8" />

-------

## Other possible architecture choices
- Cloud Function instead of Cloud Run – simpler and cheaper, but only good for very small tasks. Cloud Run fits better here.
- Dataflow instead of Cloud Run – powerful for large or streaming pipelines, but overkill for small CSV batches. Cloud Run is lighter and cheaper.
- Cloud Composer instead of Scheduler – great for complex workflows, but too heavy and costly. Scheduler is enough for a two-job pipeline.
- dbt instead of Dataform – big ecosystem and testing features, but requires extra setup. Dataform is native in BigQuery and easier to use.
- Looker Studio instead of Power BI – free and native to GCP, but the free version is limited in complex visuals. Power BI offers richer, more advanced visualizations.

---------

### Future Improvements
- adding more dimensions such as ```dim_actors```, ```dim_director```, ```dim_language```, ```dim_country``` for deeper analytics.
- stream CSV processing for large files (if possible in GCS).
- introduce stable IDs for objects in many to many relationships in ```dim_movies``` (for example movies with multiple genres).




