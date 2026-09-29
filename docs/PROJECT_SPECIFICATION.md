# WeatherSentinel

## National Weather Intelligence, Verification & Analytics Platform

**SIH Problem Statement:** SIH26069  
**Theme:** Disaster Management  
**Category:** Software  
**Status:** Under Development  
**Target Completion:** 25 October 2026

---

# 1. Problem Statement

Weather information is generated from multiple heterogeneous sources such as
weather APIs, meteorological observations, public datasets and citizen reports.

The objective of WeatherSentinel is to build a scalable platform capable of
ingesting, processing, storing, verifying, classifying and visualizing
weather-related information.

The platform will focus on weather events including:

- Rainfall
- Thunderstorms
- Flooding
- Heatwaves
- Fog
- Dust storms
- Strong winds

The system will use Data Engineering and Artificial Intelligence/Machine
Learning techniques to identify anomalies, detect duplicate reports,
classify weather events and estimate the credibility of incoming reports.

---

# 2. Project Objective

WeatherSentinel aims to provide a centralized weather intelligence platform
that transforms heterogeneous weather data into actionable and verifiable
information.

The major objectives are:

1. Collect weather observations from multiple sources.
2. Build a reliable data ingestion pipeline.
3. Process large volumes of weather data.
4. Store structured and geospatial weather information.
5. Detect abnormal weather observations.
6. Classify weather events using Machine Learning.
7. Detect duplicate or highly similar reports.
8. Estimate the credibility of citizen-generated reports.
9. Provide geospatial visualization of weather events.
10. Provide APIs for accessing weather intelligence.
11. Provide role-based access to the platform.
12. Deploy the system as a production-oriented application.

---

# 3. Core System

The platform will consist of the following major components:

- Data ingestion layer
- Streaming layer
- Data processing layer
- Storage layer
- Machine Learning layer
- Verification engine
- FastAPI backend
- Geospatial analytics layer
- Web dashboard
- Authentication and authorization
- Monitoring and logging

---

# 4. Data Sources

The project will initially use:

## 4.1 Historical Weather Data

Historical weather datasets will be used for:

- Exploratory Data Analysis
- Feature engineering
- Model training
- Model evaluation
- Historical analytics

## 4.2 Weather API Data

A weather API will provide current weather observations.

Expected attributes include:

- Timestamp
- Latitude
- Longitude
- Temperature
- Humidity
- Atmospheric pressure
- Wind speed
- Wind direction
- Rainfall
- Visibility
- Weather condition

## 4.3 Citizen Weather Reports

The platform will provide an API through which users can submit
weather-related reports.

A report may contain:

- Location
- Timestamp
- Event type
- Description
- Optional image
- GPS coordinates

---

# 5. Data Engineering Pipeline

The initial pipeline will follow:

Data Sources
    ↓
Data Ingestion
    ↓
Kafka
    ↓
Data Validation
    ↓
PySpark Processing
    ↓
PostgreSQL / PostGIS
    ↓
ML & Verification
    ↓
FastAPI
    ↓
Dashboard

---

# 6. Machine Learning Components

## 6.1 Weather Event Classification

The system will classify weather observations into categories such as:

- Normal
- Heavy Rainfall
- Thunderstorm
- Flood Risk
- Heatwave
- Fog
- Strong Wind

Candidate models:

- Random Forest
- XGBoost
- Other suitable supervised learning models

Model selection will be based on measured validation performance.

---

## 6.2 Weather Anomaly Detection

The system will identify observations that significantly deviate from
historical patterns.

Candidate approaches:

- Isolation Forest
- Local Outlier Factor
- Statistical anomaly detection

---

## 6.3 Duplicate Report Detection

The system will identify reports that are likely to describe the same
weather event.

Signals may include:

- Geographic proximity
- Temporal proximity
- Text similarity
- Image similarity

---

## 6.4 Report Credibility

The system will compare citizen reports with independent weather
observations and other reports.

Possible evidence:

- Nearby weather observations
- Historical weather patterns
- Other reports
- Geographic proximity
- Temporal consistency
- ML confidence

The system will produce a credibility/verification result rather than
treating every submitted report as automatically valid.

---

# 7. Database

Primary database:

**PostgreSQL**

Geospatial extension:

**PostGIS**

The database will store:

- Users
- Weather observations
- Weather events
- Locations
- Citizen reports
- Verification results
- ML predictions
- Anomaly results
- Processing metadata

---

# 8. Backend

The backend will be developed using:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

The backend will expose APIs for:

- Authentication
- Weather observations
- Weather events
- Citizen reports
- Verification
- Analytics
- Geospatial queries
- ML predictions

---

# 9. Data Engineering Technology

The initial technology stack will include:

- Apache Kafka
- PySpark
- PostgreSQL
- PostGIS
- Apache Airflow

Technologies will be introduced progressively based on actual project
requirements rather than being added only for resume purposes.

---

# 10. Frontend

The dashboard will provide:

- Interactive weather map
- Weather event visualization
- Event filtering
- Historical analytics
- Weather statistics
- Event details
- Verification status
- Anomaly information
- Administrative controls

Planned technologies:

- React
- TypeScript
- Leaflet or Mapbox
- Plotly or equivalent visualization library

---

# 11. Authentication

The system will implement role-based access.

### Citizen

- Submit reports
- View submitted reports
- Track verification status

### Analyst

- View weather analytics
- Review reports
- Inspect ML results

### Administrator

- Manage users
- Review reports
- Manage system data
- Monitor processing pipelines

Authentication will use secure token-based authentication.

---

# 12. Non-Functional Requirements

The system should be:

- Scalable
- Modular
- Testable
- Secure
- Observable
- Maintainable
- Containerized
- Deployable

The system should also provide:

- Input validation
- Error handling
- Logging
- API documentation
- Automated testing

---

# 13. Development Phases

## Phase 1 — Foundation

- Repository setup
- Requirements
- Architecture
- Database design
- FastAPI foundation

## Phase 2 — Data Pipeline

- Historical data ingestion
- Weather API ingestion
- Data validation
- PostgreSQL storage
- Kafka streaming

## Phase 3 — Data Processing

- PySpark processing
- Transformation
- Aggregation
- Data quality checks

## Phase 4 — AI/ML

- Feature engineering
- Weather event classification
- Anomaly detection
- Duplicate detection
- Report verification

## Phase 5 — Application

- FastAPI APIs
- Authentication
- Dashboard
- GIS visualization
- Analytics

## Phase 6 — Production

- Docker
- Automated testing
- CI/CD
- Monitoring
- Cloud deployment

## Phase 7 — Finalization

- Documentation
- Performance testing
- Security review
- Demo preparation
- Resume documentation

---

# 14. Success Criteria

The project will be considered complete when:

- Weather data can be ingested successfully.
- Data is validated and stored.
- Streaming ingestion is functional.
- Processed data can be queried through APIs.
- Weather events can be classified.
- Anomalies can be detected.
- Duplicate reports can be identified.
- Citizen reports can be evaluated against available evidence.
- Weather events can be visualized geographically.
- Users can authenticate according to their roles.
- The application can be deployed.
- Automated tests cover critical functionality.
- Technical documentation is complete.

---

# 15. Project Principle

WeatherSentinel will prioritize functional engineering over technology
collection.

A technology will only be introduced when it solves a real requirement
within the system.

Measured performance, reproducibility, testing and documented engineering
decisions will take priority over artificial complexity.