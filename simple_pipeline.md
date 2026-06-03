# NYC Taxi Data Pipeline — Luồng chạy đơn giản

```
1. TẢI DATA        NYC TLC website → 3 file parquet (~9.5M chuyến taxi)
                         ↓
2. LÀM SẠCH        pandas xử lý → valid 9M / invalid 493K / duplicate 6
                         ↓
3. LƯU VÀO DB      PostgreSQL: raw.zone_lookup (265 zones)
                             silver.trips (9M rows)
                         ↓
4. BIẾN ĐỔI (dbt)  staging → dims → facts → marts (8 tables)
                         ↓
5. XUẤT GOLD       dbt tables → parquet files (data/gold/)
                         ↓
6. TRỰC QUAN       Metabase dashboard → localhost:3000
```

**Tóm lại**: Tải data → Làm sạch → Lưu DB → Biến đổi → Trực quan hóa

Mọi thứ chạy tự động bằng 1 lệnh:
```bash
docker-compose up -d pipeline
```
