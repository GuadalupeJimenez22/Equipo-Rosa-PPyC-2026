# Tarea 06 - Conexión con base de datos

## Descripción
Programa paralelo que obtiene precios de acciones del S&P 500 desde Yahoo Finance y los inserta en una base de datos PostgreSQL.

## Base de datos
La base de datos se ejecuta con Docker usando PostgreSQL.

Tabla utilizada:

```sql
CREATE TABLE IF NOT EXISTS acciones (
    nombre text,
    valor float
);