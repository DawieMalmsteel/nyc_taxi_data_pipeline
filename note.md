# NYC Taxi Data Pipeline — Các note đáng chú ý

## Data Storage

Dữ liệu được lưu tại **nhiều nơi**, không phải chỉ 1 chỗ:

### 1. Data Lake (trên ổ đĩa host)

```
data/
├── raw/yellow_taxi/      153MB   3 files raw parquet (gitignored)
├── silver/trips/          357MB   8 files cleaned parquet (gitignored)
├── gold/                   68KB   4 files mart parquet (gitignored)
├── quarantine/             22MB   Invalid records (gitignored)
├── lookup/                 16KB   Zone CSV (tracked in git ✅)
└── quality_report.json      4KB   Quality metrics (gitignored)
```

**Lưu ý**: Toàn bộ `data/raw/`, `data/silver/`, `data/gold/`, `data/quarantine/` đều bị gitignore vì quá lớn. Chỉ có `data/lookup/taxi_zone_lookup.csv` được track.

### 2. PostgreSQL (Docker Volume)

```
nyc_taxi_data_pipeline_pgdata → ~1.5GB PostgreSQL data
```

3 schemas trong PostgreSQL:

| Schema | Tables | Rows | Description |
|--------|--------|------|-------------|
| `raw` | zone_lookup | 265 | Zone lookup từ CSV |
| `silver` | trips | ~9M | Cleaned trips từ data lake |
| `analytics` | 8 tables | varies | dbt marts (dims + facts) |

### 3. Metabase (Docker Volume)

```
nyc_taxi_data_pipeline_metabase-data → H2 database (cấu hình dashboard)
```

---

## Docker Infrastructure

3 services chạy trên cùng mạng Docker:

```
nyc_taxi_postgres    → PostgreSQL 16   (port 5432)
nyc_taxi_pipeline    → Pipeline script  (chạy xong thì exit)
nyc_taxi_metabase    → Metabase        (port 3000)
```

### Networking quan trọng

- Services kết nối với nhau qua **tên container**, không phải `localhost`
- PostgreSQL host = `postgres` (không phải `localhost`)
- Pipeline container chỉ chạy 1 lần rồi exit (không phải daemon)

---

## Data Processing Notes

### PySpark KHÔNG dùng được

Dự án ban đầu dự tính dùng PySpark nhưng **PySpark 4.x incompatible với JDK 21+**:
```
UnsupportedOperationException: getSubject is not supported
```
→ Chuyển sang **pandas + pyarrow** — xử lý ~9.5M records vẫn ổn.

### COPY Protocol thay vì to_sql

- `to_sql` với `method="multi"` rất chậm (~50k rows/phút)
- PostgreSQL `COPY FROM STDIN` nhanh hơn **10-50x** (~200k rows/30s)
- Implementation: DataFrame → StringIO CSV → `copy_expert()`

### NULL Handling trong COPY

- CSV mode PostgreSQL dùng **empty string** làm NULL, không phải `\N`
- pandas `to_csv(na_rep="")` + COPY `NULL ''` — nếu dùng `\N` sẽ lỗi integer columns

### PostgreSQL round() function

- `round(double precision, integer)` **KHÔNG tồn tại** trong PostgreSQL
- Phải cast sang `numeric` trước: `round((value)::numeric, 2)`

---

## dbt Notes

### Schema Convention

- Profile schema: `analytics`
- Staging models → views trong `analytics`
- Mart models → tables trong `analytics`
- Không dùng `+schema` override (tránh `analytics_analytics` prefix)

### dbt Version

- Phải dùng `dbt-postgres==1.9.*` (NOT 2.0)
- dbt Fusion 2.0 **không hỗ trợ postgres adapter**
- dbt-core version: 1.11.11

### Pipeline Skip Logic

Pipeline tự động skip các bước đã hoàn thành:
- Download → skip nếu `data/raw/yellow_taxi/` có ≥3 files
- Clean → skip nếu `data/silver/trips/` có parquet files
- Load → skip nếu `silver.trips` có >100K rows trong PostgreSQL
- dbt → luôn chạy (rebuild models)

---

## Metabase Connection

| Field | Value | Notes |
|-------|-------|-------|
| Host | `postgres` | KHÔNG phải localhost |
| Port | `5432` | |
| Database | `nyc_taxi` | |
| Username | `nyc_user` | |
| Password | `nyc_password` | |

Sau khi connect, dùng tables trong schema `analytics` để tạo dashboard.

---

## Common Issues

### Pipeline restart không cần rebuild

```bash
# Nếu data đã có, chỉ cần restart
docker-compose restart pipeline

# Pipeline sẽ skip download/clean/load, chạy dbt trực tiếp
```

### xóa sạch data

```bash
docker-compose down -v          # Xóa containers + volumes
rm -rf data/raw data/silver data/gold data/quarantine  # Xóa data lake
```

### Rebuild image sau khi sửa code

```bash
docker-compose build pipeline && docker-compose up -d pipeline
```

---

## Git Ignore Logic

```gitignore
# Data too large for git
data/raw/          # ~153MB raw parquet
data/silver/       # ~357MB cleaned parquet
data/gold/         # ~68KB gold exports
data/quarantine/   # ~22MB invalid records

# Tracked
!data/lookup/      # Zone CSV (16KB)
```

Data trên disk chỉ có trên máy local, không push lên git. Mỗi lần chạy `docker-compose up` sẽ download lại từ đầu.
