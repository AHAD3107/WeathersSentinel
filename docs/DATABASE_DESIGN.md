# WeatherSentinel Database Design

## 1. Database

Primary Database:

PostgreSQL

Geospatial Extension:

PostGIS

---

# 2. Entity Overview

The initial database contains:

1. Users
2. Locations
3. Weather Observations
4. Weather Events
5. Citizen Reports
6. Verification Results
7. ML Predictions

---

# 3. Users

Stores authenticated platform users.

Fields:

- id
- name
- email
- password_hash
- role
- created_at
- updated_at

Roles:

- citizen
- analyst
- admin

---

# 4. Locations

Stores geographic information.

Fields:

- id
- name
- district
- state
- country
- latitude
- longitude
- geometry
- created_at

PostGIS geometry will be used for spatial queries.

---

# 5. Weather Observations

Stores raw and processed weather observations.

Fields:

- id
- source
- observed_at
- location_id
- temperature
- humidity
- pressure
- rainfall
- wind_speed
- wind_direction
- visibility
- weather_condition
- raw_data
- created_at

---

# 6. Weather Events

Represents detected or classified weather events.

Fields:

- id
- event_type
- location_id
- start_time
- end_time
- severity
- confidence_score
- source
- created_at

Event types may include:

- rainfall
- thunderstorm
- flooding
- heatwave
- fog
- dust_storm
- strong_wind

---

# 7. Citizen Reports

Stores reports submitted by users.

Fields:

- id
- user_id
- location_id
- event_type
- description
- reported_at
- image_url
- status
- created_at

Possible statuses:

- pending
- verified
- rejected
- suspicious

---

# 8. Verification Results

Stores the result of the report verification process.

Fields:

- id
- report_id
- credibility_score
- verification_status
- supporting_observations
- verification_reason
- model_version
- created_at

Possible verification statuses:

- pending
- likely_valid
- uncertain
- likely_misleading

---

# 9. ML Predictions

Stores machine-learning predictions.

Fields:

- id
- observation_id
- model_name
- model_version
- predicted_event
- confidence_score
- created_at

---

# 10. Relationships

User

    1 ──────── N

Citizen Reports


Location

    1 ──────── N

Weather Observations


Location

    1 ──────── N

Weather Events


Citizen Report

    1 ──────── 1

Verification Result


Weather Observation

    1 ──────── N

ML Predictions

---

# 11. Initial Design Principle

The database should separate:

- raw observations
- detected events
- user-generated reports
- ML predictions
- verification results

This prevents the system from mixing source data with derived intelligence.

---

# 12. Future Extensions

Potential future tables:

- data_sources
- processing_jobs
- model_versions
- audit_logs
- notifications
- weather_stations
- pipeline_metrics

These will only be introduced when required.