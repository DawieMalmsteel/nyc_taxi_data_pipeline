 🔗 Thông tin PostgreSQL cho Metabase

 ┌───────────────┬──────────────┐
 │ Field         │ Value        │
 ├───────────────┼──────────────┤
 │ Display name  │ NYC Taxi     │
 ├───────────────┼──────────────┤
 │ Database type │ PostgreSQL   │
 ├───────────────┼──────────────┤
 │ Host          │ postgres     │
 ├───────────────┼──────────────┤
 │ Port          │ 5432         │
 ├───────────────┼──────────────┤
 │ Database name │ nyc_taxi     │
 ├───────────────┼──────────────┤
 │ Username      │ nyc_user     │
 ├───────────────┼──────────────┤
 │ Password      │ nyc_password │
 └───────────────┴──────────────┘

 ────────────────────────────────────────────────────────────────────────────────

 ### ⚠️ Lưu ý quan trọng

 Vì Metabase chạy trong Docker, nên Host phải là postgres (tên container), không phải localhost.

 ────────────────────────────────────────────────────────────────────────────────

 ### 📋 Schema có sẵn trong database

 ┌───────────┬──────────────────────────────────────────────────────────┐
 │ Schema    │ Tables                                                   │
 ├───────────┼──────────────────────────────────────────────────────────┤
 │ silver    │ trips (9M rows)                                          │
 ├───────────┼──────────────────────────────────────────────────────────┤
 │ analytics │ fact_trips, dim_zone, dim_date, dim_payment_type, mart_* │
 ├───────────┼──────────────────────────────────────────────────────────┤
 │ raw       │ zone_lookup                                              │
 └───────────┴──────────────────────────────────────────────────────────┘

 ────────────────────────────────────────────────────────────────────────────────

 ### 🚀 Bước tiếp theo

 1. Mở Metabase: http://localhost:3000
 2. Setup lần đầu (chọn "I'll add my data later" nếu muốn skip)
 3. Vào Admin → Databases → Add database
 4. Nhập thông tin trên
 5. Click Save → Explore
