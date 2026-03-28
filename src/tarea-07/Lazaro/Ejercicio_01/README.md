# Ejercicio 01 - Análisis de Latencia en APIs REST

## Descripción
Este programa compara el tiempo de ejecución entre una versión secuencial y una versión concurrente usando hilos para consultar una API REST de clima.

## Objetivo
Analizar si consultar varias APIs al mismo tiempo reduce el tiempo total de ejecución.

## Tecnologías usadas
- Python
- requests
- threading

## Ciudades consultadas
- CDMX
- Nueva York
- Londres
- Tokio

## Ejecución

```bash
pip install -r requirements.txt
python3 main.py