const express = require('express');
const { Pool } = require('pg');
const path = require('path');

const pool = new Pool({
  host: 'localhost',
  port: 5450,
  user: 'postgres',
  password: 'postgres',
  database: 'ppyc_db',
  connectionTimeoutMillis: 2000,
  idleTimeoutMillis: 30000,
  max: 5,
});

const app = express();
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/weeks', async (req, res) => {
  const { year } = req.query;
  try {
    const { rows } = await pool.query(`
      SELECT DISTINCT c.year, EXTRACT(WEEK FROM c.date)::INT AS week
      FROM urbanflow.trip_statistics ts
      JOIN urbanflow.calendar c ON ts.date = c.date
      WHERE ($1::INT IS NULL OR c.year = $1)
      ORDER BY c.year, week
    `, [year || null]);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/stats', async (req, res) => {
  const { year, week, hour, limit = 50 } = req.query;
  try {
    const { rows } = await pool.query(`
      SELECT ts.hour, ts.LocationID, ts.trip_count,
             z.zone, z.borough
      FROM urbanflow.trip_statistics ts
      JOIN urbanflow.zones z ON ts.LocationID = z.LocationID
      JOIN urbanflow.calendar c ON ts.date = c.date
      WHERE c.year = $1
        AND ($2::INT IS NULL OR EXTRACT(WEEK FROM c.date)::INT = $2)
        AND ($3::INT IS NULL OR ts.hour = $3)
      ORDER BY ts.trip_count DESC
      LIMIT $4
    `, [year || 2024, week || null, hour || null, limit]);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/stats-by-hour', async (req, res) => {
  const { year, week } = req.query;
  try {
    const { rows } = await pool.query(`
      SELECT ts.hour, SUM(ts.trip_count)::INT AS total
      FROM urbanflow.trip_statistics ts
      JOIN urbanflow.calendar c ON ts.date = c.date
      WHERE c.year = $1
        AND ($2::INT IS NULL OR EXTRACT(WEEK FROM c.date)::INT = $2)
      GROUP BY ts.hour
      ORDER BY ts.hour
    `, [year || 2024, week || null]);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/summary', async (req, res) => {
  const { year, week } = req.query;
  try {
    const { rows } = await pool.query(`
      SELECT z.borough, SUM(ts.trip_count)::INT AS total
      FROM urbanflow.trip_statistics ts
      JOIN urbanflow.zones z ON ts.LocationID = z.LocationID
      JOIN urbanflow.calendar c ON ts.date = c.date
      WHERE c.year = $1
        AND ($2::INT IS NULL OR EXTRACT(WEEK FROM c.date)::INT = $2)
      GROUP BY z.borough
      ORDER BY total DESC
    `, [year || 2024, week || null]);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/zones/geojson', async (req, res) => {
  const { year, week, hour } = req.query;
  try {
    const { rows } = await pool.query(`
      SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(json_agg(
          json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(zg.geometry)::json,
            'properties', json_build_object(
              'LocationID', z.LocationID,
              'zone', z.zone,
              'borough', z.borough,
              'trip_count', COALESCE(ts_total.total, 0)
            )
          )
        ) FILTER (WHERE zg.geometry IS NOT NULL), '[]'::json)
      ) AS geojson
      FROM urbanflow.zones z
      JOIN urbanflow.zones_geometry zg ON z.LocationID = zg.LocationID
      LEFT JOIN (
        SELECT ts.LocationID, SUM(ts.trip_count)::INT AS total
        FROM urbanflow.trip_statistics ts
        JOIN urbanflow.calendar c ON ts.date = c.date
        WHERE c.year = $1
          AND ($2::INT IS NULL OR EXTRACT(WEEK FROM c.date)::INT = $2)
          AND ($3::INT IS NULL OR ts.hour = $3)
        GROUP BY ts.LocationID
      ) ts_total ON z.LocationID = ts_total.LocationID
    `, [year || 2024, week || null, hour || null]);
    res.json(rows[0]?.geojson || { type: 'FeatureCollection', features: [] });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const servidor = app.listen(0, () => {
  console.log('🚀 UrbanFlow API en http://localhost:' + servidor.address().port);
});
