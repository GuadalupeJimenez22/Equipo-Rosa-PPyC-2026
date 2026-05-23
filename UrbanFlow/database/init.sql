-- ==========================================
-- UrbanFlow - Modelo Relacional Normalizado
-- Base de datos para análisis de viajes NYC
-- ==========================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS urbanflow;
SET search_path TO urbanflow, public;

-- ==========================================
-- Dimensión: Zonas de taxi
-- ==========================================
CREATE TABLE IF NOT EXISTS zones (
    LocationID   INT PRIMARY KEY,
    Zone         VARCHAR(100),
    Borough      VARCHAR(50),
    service_zone VARCHAR(50)
);

-- ==========================================
-- Geometría de zonas (PostGIS)
-- ==========================================
CREATE TABLE IF NOT EXISTS zones_geometry (
    LocationID   INT PRIMARY KEY REFERENCES zones(LocationID),
    geometry     GEOMETRY(POLYGON, 4326)
);

CREATE INDEX idx_zones_borough ON zones(Borough);

-- ==========================================
-- Dimensión: Calendario
-- ==========================================
CREATE TABLE IF NOT EXISTS calendar (
    date       DATE PRIMARY KEY,
    year       INT NOT NULL,
    month      INT NOT NULL,
    day        INT NOT NULL,
    is_weekend BOOLEAN
);

-- ==========================================
-- Tabla de hechos: Viajes individuales
-- ==========================================
CREATE TABLE IF NOT EXISTS trips (
    VendorID              INT,
    tpep_pickup_datetime  TIMESTAMP NOT NULL,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count       INT,
    trip_distance         DECIMAL(8,2),
    RatecodeID            INT,
    store_and_fwd_flag    VARCHAR(10),
    PULocationID          INT NOT NULL REFERENCES zones(LocationID),
    DOLocationID          INT NOT NULL REFERENCES zones(LocationID),
    payment_type          INT,
    fare_amount           DECIMAL(8,2),
    extra                 DECIMAL(6,2),
    mta_tax               DECIMAL(6,2),
    tip_amount            DECIMAL(8,2),
    tolls_amount          DECIMAL(8,2),
    improvement_surcharge DECIMAL(6,2),
    total_amount          DECIMAL(8,2),
    congestion_surcharge  DECIMAL(6,2),
    Airport_fee           DECIMAL(6,2),
    cbd_congestion_fee    DECIMAL(6,2)
);

CREATE INDEX idx_trips_pickup  ON trips(tpep_pickup_datetime);
CREATE INDEX idx_trips_puloc   ON trips(PULocationID);
CREATE INDEX idx_trips_doloc   ON trips(DOLocationID);

-- ==========================================
-- Tabla de agregados: Estadísticas hora/zona
-- (producida por el pipeline Map-Reduce)
-- ==========================================
CREATE TABLE IF NOT EXISTS trip_statistics (
    stat_id    BIGSERIAL PRIMARY KEY,
    LocationID INT NOT NULL REFERENCES zones(LocationID),
    date       DATE NOT NULL REFERENCES calendar(date),
    hour       INT NOT NULL CHECK (hour >= 0 AND hour <= 23),
    trip_count INT NOT NULL DEFAULT 0,

    UNIQUE (LocationID, date, hour)
);

CREATE INDEX idx_stats_loc_date ON trip_statistics(LocationID, date);
