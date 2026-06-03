# NYC Taxi Data Pipeline — Hướng dẫn chạy dự án

## Yêu cầu

- Docker & Docker Compose đã cài đặt
- Ít nhất 10GB dung lượng trống (data raw ~2GB, PostgreSQL ~2GB)

---

## Cách 1: Chạy toàn bộ trên Docker (Khuyến nghị)

### Bước 1: Clone repository

```bash
git clone https://github.com/DawieMalmsteel/nyc_taxi_data_pipeline.git
cd nyc_taxi_data_pipeline
```

### Bước 2: Build image Docker

```bash
docker-compose build pipeline
```

### Bước 3: Start infrastructure (PostgreSQL + Metabase)

```bash
docker-compose up -d postgres metabase
```

Chờ PostgreSQL ready (healthcheck tự động):
```bash
docker ps  # Kiểm tra "healthy" status
```

### Bước 4: Chạy pipeline đầy đủ

```bash
docker-compose up -d pipeline
```

Pipeline sẽ chạy tuần tự:
1. Download data (~9.5M records từ NYC TLC)
2. Clean & validate (pandas + pyarrow)
3. Load vào PostgreSQL (~25 phút, COPY protocol)
4. dbt deps + run + test (~2 phút)
5. Export gold parquet

### Bước 5: Theo dõi tiến trình

```bash
# Xem logs real-time
docker logs -f nyc_taxi_pipeline

# Hoặc query trực tiếp PostgreSQL
docker exec nyc_taxi_postgres psql -U nyc_user -d nyc_taxi -c \
  "SELECT COUNT(*) FROM silver.trips;"
```

### Bước 6: Kiểm tra kết quả

```bash
# Kiểm tra tất cả tables
docker exec nyc_taxi_postgres psql -U nyc_user -d nyc_taxi -c \
  "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('raw','silver','analytics');"

# Chạy analytics queries
docker exec nyc_taxi_postgres psql -U nyc_user -d nyc_taxi -f /dev/stdin < analytics/queries.sql

# Hoặc vào container chạy
docker exec -it nyc_taxi_postgres psql -U nyc_user -d nyc_taxi
```

### Bước 7: Mở Metabase

```
http://localhost:3000
```

Kết nối PostgreSQL khi Metabase hỏi:

| Field | Value |
|-------|-------|
| Database type | PostgreSQL |
| Host | `postgres` |
| Port | `5432` |
| Database name | `nyc_taxi` |
| Username | `nyc_user` |
| Password | `nyc_password` |

> **Lưu ý**: Host điền `postgres` (tên container), KHÔNG điền `localhost`.

---

## Cách 2: Chạy từng bước (Local Development)

### Yêu cầu local

```bash
pip install pandas pyarrow psycopg2-binary sqlalchemy dbt-postgres==1.9.*
```

### Bước 1: Download data

```bash
python scripts/download_data.py
```

Files sẽ được tải về:
- `data/raw/yellow_taxi/year=2024/month=01/yellow_tripdata_2024-01.parquet`
- `data/raw/yellow_taxi/year=2024/month=02/yellow_tripdata_2024-02.parquet`
- `data/raw/yellow_taxi/year=2024/month=03/yellow_tripdata_2024-03.parquet`
- `data/lookup/taxi_zone_lookup.csv`

### Bước 2: Start PostgreSQL

```bash
docker-compose up -d postgres
```

### Bước 3: Clean & validate data

```bash
python jobs/spark_clean.py
```

Output:
- `data/silver/trips/` — cleaned parquet (~9M records)
- `data/quarantine/invalid_trips/` — invalid records (~493K)
- `data/quality_report.json` — quality metrics

### Bước 4: Load vào PostgreSQL

```bash
python scripts/load_to_postgres.py
```

### Bước 5: Run dbt

```bash
cd dbt_project

dbt deps
dbt run
dbt test

cd ..
```

### Bước 6: Export gold layer

```bash
python scripts/export_gold.py
```

### Bước 7: Run analytics

```bash
docker exec nyc_taxi_postgres psql -U nyc_user -d nyc_taxi -c \
  "SELECT pickup_date, total_trips, ROUND(total_revenue, 2) AS revenue FROM analytics.mart_revenue_by_day ORDER BY pickup_date LIMIT 10;"
```

---

## Docker Commands tham khảo

```bash
# Kiểm tra trạng thái containers
docker ps

# Xem logs
docker logs nyc_taxi_pipeline
docker logs -f nyc_taxi_pipeline  # real-time

# Restart pipeline (skip download/clean nếu data đã có)
docker-compose restart pipeline

# Stop tất cả
docker-compose down

# Stop và xóa volumes (xóa sạch data)
docker-compose down -v

# Rebuild sau khi sửa code
docker-compose build pipeline && docker-compose up -d pipeline

# Vào PostgreSQL shell
docker exec -it nyc_taxi_postgres psql -U nyc_user -d nyc_taxi

# Vào pipeline container
docker exec -it nyc_taxi_pipeline bash
```

---

## Troubleshooting

### Pipeline timeout khi load data
- Load 9M rows mất ~25 phút qua COPY protocol
- Nếu bị timeout, chạy lại: `docker-compose restart pipeline`
- Pipeline tự skip download/clean nếu data đã có

### dbt error "round(double precision, integer)"
- Đã fix trong codebase — đảm bảo pull latest code
- PostgreSQL `round()` cần `::numeric` cast

### Metabase không kết nối được PostgreSQL
- Host phải là `postgres` (tên container), không phải `localhost`
- Đảm bảo cả 2 containers cùng mạng Docker

### Pipeline container exited nhưng chưa xong
```bash
docker logs nyc_taxi_pipeline  # Xem error
docker-compose restart pipeline  # Chạy lại
```

---

## Database Schema

```
raw
├── zone_lookup (265 rows)

silver
├── trips (~9M rows)

analytics
├── stg_trips (view)
├── stg_zones (view)
├── dim_date (75 rows)
├── dim_payment_type (5 rows)
├── dim_zone (265 rows)
├── fact_trips (~9M rows)
├── mart_revenue_by_day (75 rows)
├── mart_revenue_by_zone (519 rows)
├── mart_trips_by_hour (24 rows)
└── mart_payment_type_summary (5 rows)
```

---

## File Structure

```
nyc_taxi_pipeline/
├── docker-compose.yml        # Docker infrastructure
├── Dockerfile                # Pipeline image
├── config.yaml               # Pipeline configuration
├── requirements.txt          # Python dependencies
├── scripts/
│   ├── entrypoint.py         # Docker entrypoint (orchestrator)
│   ├── download_data.py      # Download raw data
│   ├── load_to_postgres.py   # Bulk COPY load
│   ├── export_gold.py        # Export gold parquet
│   ├── run_spark_job.py      # Spark job runner
│   ├── run_quality_checks.py # Quality check runner
│   └── init_db.sql           # PostgreSQL schema init
├── jobs/
│   └── spark_clean.py        # Data cleaning (pandas+pyarrow)
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/          # stg_trips, stg_zones
│       └── marts/            # dims, facts, marts
├── analytics/
│   └── queries.sql           # 10 business questions
└── data/                     # Data lake (gitignored)
    ├── raw/                  # Raw parquet
    ├── silver/               # Cleaned parquet
    ├── gold/                 # Mart parquet exports
    ├── quarantine/           # Invalid records
    ├── lookup/               # Zone lookup CSV (tracked)
    └── quality_report.json   # Quality metrics
```
