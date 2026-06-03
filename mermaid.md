# NYC Taxi Data Pipeline — Luồng chạy

## 1. Luồng tổng quan (Overview Flow)

```mermaid
flowchart TB
    subgraph SOURCE[" NYC TLC Data Source"]
        S1["yellow_tripdata_2024-01.parquet<br/>~3.1M records"]
        S2["yellow_tripdata_2024-02.parquet<br/>~3.0M records"]
        S3["yellow_tripdata_2024-03.parquet<br/>~3.4M records"]
        S4["taxi_zone_lookup.csv<br/>265 zones"]
    end

    subgraph DOWNLOAD["1️⃣ Download"]
        D1["download_data.py<br/>urllib.request"]
    end

    subgraph RAW[" Raw Zone (data lake)"]
        R1["data/raw/yellow_taxi/<br/>year=2024/month=01/02/03"]
        R2["data/lookup/taxi_zone_lookup.csv"]
    end

    subgraph CLEAN["2️⃣ Cleaning Job"]
        C1["spark_clean.py<br/>(pandas + pyarrow)"]
        C2["Rename columns lowercase"]
        C3["Add trip_id<br/>(SHA-256 hash)"]
        C4["Add ingestion_ts<br/>source_file"]
        C5["Extract pickup_date<br/>pickup_hour, year, month"]
        C6["Join zone lookup"]
        C7["Apply 9 quality rules"]
        C8["Remove duplicates"]
    end

    subgraph SILVER[" Silver Zone (cleaned)"]
        SL1["data/silver/trips/<br/>~9M valid records"]
        SL2["data/quarantine/invalid_trips/<br/>~493K invalid records"]
        SL3["data/quality_report.json"]
    end

    subgraph LOAD["3️⃣ Load to DB"]
        L1["load_to_postgres.py<br/>COPY protocol"]
    end

    subgraph POSTGRES[" PostgreSQL"]
        PG1["raw.zone_lookup<br/>265 rows"]
        PG2["silver.trips<br/>~9M rows"]
    end

    subgraph DBT["4️⃣ dbt Transform"]
        DB1["dbt deps"]
        DB2["dbt run<br/>10 models"]
        DB3["dbt test<br/>25 tests"]
    end

    subgraph ANALYTICS[" Analytics Tables"]
        A1["analytics.stg_trips<br/>analytics.stg_zones"]
        A2["analytics.dim_zone<br/>analytics.dim_date<br/>analytics.dim_payment_type"]
        A3["analytics.fact_trips<br/>~9M rows"]
        A4["analytics.mart_revenue_by_day<br/>analytics.mart_revenue_by_zone<br/>analytics.mart_trips_by_hour<br/>analytics.mart_payment_type_summary"]
    end

    subgraph GOLD["5️⃣ Export Gold"]
        G1["export_gold.py"]
    end

    subgraph GOLDZONE[" Gold Zone (parquet)"]
        GL1["data/gold/revenue_by_day/"]
        GL2["data/gold/revenue_by_zone/"]
        GL3["data/gold/trips_by_hour/"]
        GL4["data/gold/payment_type_summary/"]
    end

    subgraph DASHBOARD[" Metabase Dashboard"]
        M1["localhost:3000<br/>Dashboard UI"]
    end

    S1 --> D1
    S2 --> D1
    S3 --> D1
    S4 --> D1
    D1 --> R1
    D1 --> R2
    R1 --> C1
    R2 --> C1
    C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> C8
    C8 --> SL1
    C7 --> SL2
    C1 --> SL3
    SL1 --> L1
    PG1 --> L1
    L1 --> PG1
    L1 --> PG2
    PG2 --> DB1
    DB1 --> DB2
    DB2 --> DB3
    PG2 --> A1
    A1 --> A2
    A1 --> A3
    A2 --> A4
    A3 --> A4
    A4 --> G1
    G1 --> GL1
    G1 --> GL2
    G1 --> GL3
    G1 --> GL4
    A4 --> M1
```

---

## 2. Docker Infrastructure

```mermaid
flowchart LR
    subgraph HOST[" Host Machine"]
        direction TB
        HF["data/<br/>(mounted volume)"]
        HC["docker-compose.yml"]
    end

    subgraph DOCKER[" Docker Network"]
        direction TB

        subgraph PG[" nyc_taxi_postgres<br/>PostgreSQL 16"]
            PGV["pgdata volume<br/>~1.5GB"]
            PGI["init_db.sql<br/>(auto-run on start)"]
        end

        subgraph PIPE[" nyc_taxi_pipeline<br/>python:3.12-slim"]
            PE["entrypoint.py<br/>(orchestrator)"]
            PS["scripts/*.py"]
            PJ["jobs/spark_clean.py"]
            PDBT["dbt_project/"]
        end

        subgraph META[" nyc_taxi_metabase<br/>Metabase latest"]
            MV["metabase-data volume<br/>(H2 DB)"]
        end
    end

    HC --> PG
    HC --> PIPE
    HC --> META
    HF -.->|"mount"| PIPE
    PG -->|"port 5432"| HOST
    META -->|"port 3000"| HOST
    PIPE -->|"SQL queries"| PG
    META -->|"JDBC connection<br/>host: postgres"| PG
    PGI -->|"init schemas<br/>+ tables"| PG
```

---

## 3. dbt Model DAG

```mermaid
flowchart TD
    subgraph SOURCES[" Sources"]
        SRC1[("silver.trips<br/>~9M rows")]
        SRC2[("raw.zone_lookup<br/>265 rows")]
    end

    subgraph STAGING[" Staging (views)"]
        STG1["stg_trips<br/>Rename columns<br/>tpep_pickup → pickup"]
        STG2["stg_zones<br/>Zone lookup"]
    end

    subgraph DIMS[" Dimensions (tables)"]
        DIM1["dim_zone<br/>265 zones"]
        DIM2["dim_date<br/>75 dates<br/>year/month/day/dow/doy"]
        DIM3["dim_payment_type<br/>5 types<br/>Credit/Cash/No Charge/Dispute/Other"]
    end

    subgraph FACTS[" Fact Table"]
        FACT1["fact_trips<br/>~9M rows<br/>+ has_tip<br/>+ tip_percentage"]
    end

    subgraph MARTS[" Mart Tables"]
        M1["mart_revenue_by_day<br/>75 rows"]
        M2["mart_revenue_by_zone<br/>519 rows"]
        M3["mart_trips_by_hour<br/>24 rows"]
        M4["mart_payment_type_summary<br/>5 rows"]
    end

    SRC1 --> STG1
    SRC2 --> STG2
    STG1 --> FACT1
    STG1 --> DIM2
    STG1 --> DIM3
    STG2 --> DIM1
    FACT1 --> M1
    FACT1 --> M2
    FACT1 --> M3
    FACT1 --> M4
    DIM1 --> M2
```

---

## 4. Data Quality Pipeline

```mermaid
flowchart TD
    RAW[" Raw Data<br/>9,554,778 records"]

    subgraph RULES[" Data Quality Rules (9 rules)"]
        R1["1. pickup_time_not_null"]
        R2["2. dropoff_time_not_null"]
        R3["3. trip_duration_positive<br/>dropoff > pickup"]
        R4["4. trip_distance_gt_zero"]
        R5["5. fare_amount_gte_zero"]
        R6["6. total_amount_gte_fare"]
        R7["7. passenger_count_1_to_6"]
        R8["8. pickup_location_valid<br/>(in zone lookup)"]
        R9["9. dropoff_location_valid<br/>(in zone lookup)"]
    end

    DUP[" Duplicate Check<br/>trip_id SHA-256 unique"]

    VALID["✅ Valid Records<br/>9,062,115 (94.8%)"]
    INVALID["❌ Invalid Records<br/>492,657 (5.2%)"]
    DUPE["🔄 Duplicates Removed<br/>6 records"]

    subgraph QUARANTINE[" Quarantine"]
        Q1["data/quarantine/invalid_trips/<br/>+ quarantine_reason column"]
    end

    REPORT[" quality_report.json<br/>input/valid/invalid/null counts"]

    RAW --> RULES
    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 --> VALID
    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 --> INVALID
    VALID --> DUP
    DUP --> DUPE
    DUP --> VALID
    INVALID --> QUARANTINE
    RAW --> REPORT
    VALID --> REPORT
    INVALID --> REPORT
    DUPE --> REPORT
```

---

## 5. Entry Point Flow

```mermaid
flowchart TD
    START[" entrypoint.py"]

    WAIT["1. Wait for PostgreSQL<br/>healthcheck ready"]

    subgraph STEP1[" Step 1: Download"]
        CK_RAW{"data/raw/<br/>≥3 files?"}
        DL["download_data.py"]
    end

    subgraph STEP2[" Step 2: Clean"]
        CK_SILVER{"data/silver/<br/>parquet exists?"}
        CL["spark_clean.py"]
    end

    subgraph STEP3[" Step 3: Load"]
        CK_DB{"silver.trips<br/>>100K rows?"}
        LD["load_to_postgres.py<br/>(~25 min)"]
    end

    subgraph STEP4[" Step 4: dbt"]
        DBT_DEP["dbt deps"]
        DBT_RUN["dbt run<br/>(~2 min)"]
        DBT_TST["dbt test<br/>25 tests"]
    end

    subgraph STEP5[" Step 5: Gold"]
        GOLD["export_gold.py"]
    end

    DONE[" PIPELINE COMPLETE ✅"]

    START --> WAIT
    WAIT --> CK_RAW
    CK_RAW -->|"Yes, skip"| CK_SILVER
    CK_RAW -->|"No"| DL --> CK_SILVER
    CK_SILVER -->|"Yes, skip"| CK_DB
    CK_SILVER -->|"No"| CL --> CK_DB
    CK_DB -->|"Yes, skip"| DBT_DEP
    CK_DB -->|"No"| LD --> DBT_DEP
    DBT_DEP --> DBT_RUN --> DBT_TST --> GOLD --> DONE
```

---

## 6. PostgreSQL Schema

```mermaid
erDiagram
    raw_schema["raw"] {
        int location_id PK
        text borough
        text zone_name
        text service_zone
    }

    silver_schema["silver"] {
        text trip_id PK
        timestamp ingestion_ts
        text source_file
        timestamp tpep_pickup_datetime
        timestamp tpep_dropoff_datetime
        date pickup_date
        int pickup_hour
        int pickup_year
        int pickup_month
        double trip_duration_minutes
        int pulocationid
        int dolocationid
        text pickup_borough
        text pickup_zone
        text dropoff_borough
        text dropoff_zone
        int passenger_count
        double trip_distance
        int ratecodeid
        text store_and_fwd_flag
        double fare_amount
        double extra
        double mta_tax
        double tip_amount
        double tolls_amount
        double improvement_surcharge
        double total_amount
        int payment_type
        double congestion_surcharge
        double airport_fee
    }

    analytics_schema["analytics"] {
        text trip_id PK
        double tip_percentage
        bool has_tip
    }

    raw_schema ||--o{ silver_schema : "join on pulocationid/dolocationid"
    silver_schema ||--|| analytics_schema : "stg_trips → fact_trips"
```
