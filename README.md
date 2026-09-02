# TritonETA 🚎

> **Status: 🚧 In Progress**

A data science and data engineering project focused on improving the UC San Diego student transit experience.

TritonETA will use **UCSD Triton Transit data** to create a more useful, class-focused transit product that helps students figure out **which shuttle to take, when to leave, and when they can expect to arrive at class.**

## 🎯 Goal

Build a better transit experience for UCSD students by combining:

- 🚌 UCSD shuttle routes and schedules
- 📍 Real-time shuttle locations
- 🗺️ Campus buildings and nearby locations
- 🚶 Walking routes
- 🤖 Machine learning for more realistic arrival-time predictions

## 💡 Planned Product

Students will be able to:

- Search for a class/building
- Enter their starting location and class time
- See relevant shuttle routes and nearby stops
- View live shuttle locations
- Get predicted arrival times
- Get a recommended time to leave
- Compare walking vs. taking the shuttle

## 📊 Data Science

The ML component will focus on **predicting realistic shuttle arrival times** using historical UCSD transit data.

Potential features:

- Route
- Stop
- Time of day
- Day of week
- Vehicle location
- Historical travel time
- Historical delays

We will compare the model's predictions against scheduled arrival times.

## 🔄 Planned Data Pipeline

```text
UCSD GTFS + Real-Time Data
          ↓
     Data Ingestion
          ↓
    PostgreSQL / dbt
          ↓
   Data Cleaning + Features
          ↓
    ML ETA Prediction
          ↓
      Backend API
          ↓
    Interactive Web App
```

## 👥 Team

**3-person team**

- **Data Engineering:** data ingestion, database, pipelines, GTFS processing
- **ML / Data Science:** feature engineering, ETA prediction, model evaluation
- **Product / Frontend:** map, routing experience, UI/UX, deployment

## 📅 Current Plan

### Week 1

- [ ] Set up repository
- [ ] Explore UCSD GTFS data
- [ ] Set up database
- [ ] Start collecting real-time vehicle data

### Week 2

- [ ] Clean and process transit data
- [ ] Build historical dataset
- [ ] Develop initial ML model
- [ ] Begin frontend/map

### Week 3

- [ ] Connect ML + frontend
- [ ] Add class-focused routing
- [ ] Improve UI/UX
- [ ] Test and deploy

## 🚧 Current Status

**Nothing has been built yet.**

Currently in the **ideation and planning phase**, with the next priority being understanding the UCSD transit data and getting the real-time data collection pipeline running.
