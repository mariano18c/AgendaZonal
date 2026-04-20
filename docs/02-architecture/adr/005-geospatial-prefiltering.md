# ADR 005: Geospatial Pre-filtering over PostGIS/SpatiaLite

## Status
Accepted

## Context
AgendaZonal relies heavily on locating services "near me" (Rosario/Ibarlucea). Traditional geospatial databases like PostGIS are resource-intensive, requiring high RAM and complex background processes. SpatiaLite is a lighter alternative but complicates the deployment on Raspberry Pi 5 due to shared library dependencies and build-time issues.

## Decision
We will use a **Custom Geofencing Strategy** combining two layers:
1. **Database Layer (Bounding Box)**: A SQL query using simple `BETWEEN` operators on `latitude` and `longitude` columns. These columns are indexed to ensure O(log N) search performance.
2. **Application Layer (Haversine)**: The subset of results returned by the database is then filtered/sorted in Python using the Haversine formula to get precise distances.

### SQL Approximation
```sql
SELECT * FROM contacts 
WHERE latitude BETWEEN :min_lat AND :max_lat 
  AND longitude BETWEEN :min_lng AND :max_lng;
```

## Consequences
- **Pros**:
    - Zero external dependencies (No PostGIS/SpatiaLite required).
    - Extremely low RAM usage.
    - Simplified deployment and full compatibility with standard SQLite WAL mode.
    - Performance is more than sufficient for <100,000 local points.
- **Cons**:
    - Slight over-fetching in the corners of the Bounding Box (filtered out in Python).
    - Calculating precise distances for thousands of points in Python is slower than in C (mitigated by pre-filtering).
