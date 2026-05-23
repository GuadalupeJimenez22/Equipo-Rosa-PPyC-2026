import os
import time
import random
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm
import duckdb


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

ANIOS = [2024, 2025]
MESES = range(1, 13)

# Ahora manejamos 4 fuentes:
# 1. yellow  = Yellow Taxi
# 2. green   = Green Taxi
# 3. fhv     = For-Hire Vehicle
# 4. fhvhv   = High Volume For-Hire Vehicle, tipo Uber/Lyft
DATASETS = {
    "yellow": {
        "nombre_visual": "Yellow Taxi",
        "url_pattern": "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{anio}-{mes:02d}.parquet",
        "datetime_candidates": ["tpep_pickup_datetime"],
        "pickup_candidates": ["PULocationID", "PUlocationID", "pulocationid"],
    },
    "green": {
        "nombre_visual": "Green Taxi",
        "url_pattern": "https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_{anio}-{mes:02d}.parquet",
        "datetime_candidates": ["lpep_pickup_datetime"],
        "pickup_candidates": ["PULocationID", "PUlocationID", "pulocationid"],
    },
    "fhv": {
        "nombre_visual": "For-Hire Vehicle",
        "url_pattern": "https://d37ci6vzurychx.cloudfront.net/trip-data/fhv_tripdata_{anio}-{mes:02d}.parquet",
        "datetime_candidates": ["pickup_datetime"],
        "pickup_candidates": ["PULocationID", "PUlocationID", "pulocationid"],
    },
    "fhvhv": {
        "nombre_visual": "High Volume FHV",
        "url_pattern": "https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_{anio}-{mes:02d}.parquet",
        "datetime_candidates": ["pickup_datetime"],
        "pickup_candidates": ["PULocationID", "PUlocationID", "pulocationid"],
    },
}

DIR_TAXI_ZONES = Path("taxi_zones")
DIR_OUTPUT_WEEKLY = Path("output_weekly")
DIR_OUTPUT_TEST = Path("output_weekly_test")
DIR_TEMP = Path("tmp_downloads")
DIR_RESUMENES = Path("resumenes_weekly")

SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
SHAPEFILE_PATH = DIR_TAXI_ZONES / "taxi_zones.shp"

# Encuadre extendido para abarcar NYC completo.
NYC_XLIM = (-8270000, -8200000)
NYC_YLIM = (4930000, 5010000)


# ============================================================
# 1. SHAPEFILE DE ZONAS DE TAXI
# ============================================================

def obtener_shapefile_zonas():
    """
    Descarga, extrae y carga el shapefile oficial de zonas de taxi de NYC.

    Se convierte a EPSG:3857 porque contextily usa mapas web
    en Web Mercator.
    """
    DIR_TAXI_ZONES.mkdir(exist_ok=True)

    if not SHAPEFILE_PATH.exists():
        print("📥 Descargando shapefile de zonas de taxi de Nueva York...")
        zip_path = DIR_TAXI_ZONES / "taxi_zones.zip"

        urllib.request.urlretrieve(SHAPEFILE_URL, zip_path)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(DIR_TAXI_ZONES)

        print("✅ Shapefile descargado y extraído.")

    gdf_zonas = gpd.read_file(SHAPEFILE_PATH)
    gdf_zonas = gdf_zonas.to_crs(epsg=3857)

    columnas_necesarias = ["LocationID", "zone", "borough", "geometry"]
    columnas_existentes = [c for c in columnas_necesarias if c in gdf_zonas.columns]
    gdf_zonas = gdf_zonas[columnas_existentes]

    gdf_zonas["LocationID"] = gdf_zonas["LocationID"].astype(int)

    return gdf_zonas


# ============================================================
# 2. UTILIDADES PARA DETECTAR COLUMNAS EN PARQUET
# ============================================================

def obtener_columnas_parquet(con, parquet_path):
    """
    Lee únicamente el esquema del parquet con DuckDB.
    No carga todo el archivo a memoria.
    """
    query = f"DESCRIBE SELECT * FROM read_parquet('{parquet_path}')"
    columnas = con.query(query).df()["column_name"].tolist()
    return columnas


def elegir_columna(columnas_disponibles, candidatos, nombre_logico):
    """
    Elige la primera columna candidata que exista en el archivo.

    Esto ayuda porque entre Yellow, Green, FHV y FHVHV puede haber
    pequeñas diferencias en mayúsculas/minúsculas.
    """
    mapa_lower = {c.lower(): c for c in columnas_disponibles}

    for candidato in candidatos:
        if candidato.lower() in mapa_lower:
            return mapa_lower[candidato.lower()]

    raise ValueError(
        f"No se encontró columna para {nombre_logico}. "
        f"Candidatos: {candidatos}. "
        f"Columnas disponibles: {columnas_disponibles}"
    )


# ============================================================
# 3. PROCESAMIENTO SEMANAL OPTIMIZADO CON DUCKDB
# ============================================================

def descargar_archivo(url, destino):
    """
    Descarga un parquet desde la URL oficial hacia disco local.
    """
    urllib.request.urlretrieve(url, destino)


def procesar_parquet_semanal(con, parquet_path, dataset, anio, mes):
    """
    Resume un parquet por:
    - dataset
    - año
    - semana ISO
    - zona de pickup

    Devuelve un DataFrame pequeño:
    dataset | year | week | week_start | PULocationID | trip_count
    """
    config = DATASETS[dataset]

    columnas = obtener_columnas_parquet(con, parquet_path)

    datetime_col = elegir_columna(
        columnas,
        config["datetime_candidates"],
        nombre_logico="fecha/hora de pickup"
    )

    pickup_col = elegir_columna(
        columnas,
        config["pickup_candidates"],
        nombre_logico="zona de pickup"
    )

    # DuckDB reduce millones de filas a pocas filas agregadas.
    # yearweek funciona como llave útil: 202401, 202402, etc.
    # week_start sirve para títulos y orden cronológico.
    query = f"""
        SELECT
            '{dataset}' AS dataset,
            '{config["nombre_visual"]}' AS dataset_name,
            EXTRACT(YEAR FROM {datetime_col})::INT AS year,
            EXTRACT(WEEK FROM {datetime_col})::INT AS week,
            DATE_TRUNC('week', {datetime_col})::DATE AS week_start,
            {pickup_col}::INT AS PULocationID,
            COUNT(*)::BIGINT AS trip_count
        FROM read_parquet('{parquet_path}')
        WHERE
            {datetime_col} IS NOT NULL
            AND {pickup_col} IS NOT NULL
            AND {pickup_col} > 0
        GROUP BY
            dataset,
            dataset_name,
            year,
            week,
            week_start,
            PULocationID
    """

    return con.query(query).df()


def procesar_historico_semanal(
    datasets=("yellow", "green", "fhv", "fhvhv"),
    anios=ANIOS,
    meses=MESES,
    guardar_resumenes=True,
):
    """
    Descarga temporalmente cada archivo parquet, lo resume por semana/zona
    y elimina el archivo crudo para no saturar disco ni RAM.

    Esta es la parte estilo Map-Reduce:
    archivo grande -> resumen pequeño -> borrar archivo grande.
    """
    DIR_TEMP.mkdir(exist_ok=True)
    DIR_RESUMENES.mkdir(exist_ok=True)

    con = duckdb.connect()
    resumenes = []

    total_planeados = len(datasets) * len(list(anios)) * len(list(meses))
    total_procesados = 0

    print("🚀 Iniciando procesamiento semanal con DuckDB...")
    print(f"📦 Archivos planeados: {total_planeados}")

    for dataset in datasets:
        if dataset not in DATASETS:
            print(f"⚠️ Dataset no reconocido: {dataset}. Se omite.")
            continue

        config = DATASETS[dataset]

        for anio in anios:
            for mes in meses:
                url = config["url_pattern"].format(anio=anio, mes=mes)
                archivo_temp = DIR_TEMP / f"{dataset}_{anio}_{mes:02d}.parquet"

                print(f"📥 {dataset.upper()} {anio}-{mes:02d}...", end=" ")

                try:
                    descargar_archivo(url, archivo_temp)

                    resumen_mes = procesar_parquet_semanal(
                        con=con,
                        parquet_path=archivo_temp,
                        dataset=dataset,
                        anio=anio,
                        mes=mes,
                    )

                    resumenes.append(resumen_mes)
                    total_procesados += 1

                    if guardar_resumenes:
                        resumen_path = DIR_RESUMENES / f"resumen_{dataset}_{anio}_{mes:02d}.csv"
                        resumen_mes.to_csv(resumen_path, index=False)

                    print(f"✅ procesado. Filas resumen: {len(resumen_mes)}")

                except urllib.error.HTTPError as e:
                    print(f"⚠️ no disponible. HTTP {e.code}")

                except Exception as e:
                    print(f"❌ error: {e}")

                finally:
                    if archivo_temp.exists():
                        archivo_temp.unlink()

    if not resumenes:
        raise RuntimeError(
            "No se generó ningún resumen. Verifica conexión, URLs o disponibilidad de datos."
        )

    print(f"\n🔄 Consolidando {total_procesados} archivos procesados...")
    df = pd.concat(resumenes, ignore_index=True)

    # Consolidamos por dataset, año, semana y zona.
    conteo_semanal = (
        df.groupby(
            ["dataset", "dataset_name", "year", "week", "week_start", "PULocationID"],
            as_index=False
        )["trip_count"]
        .sum()
        .sort_values(["dataset", "week_start", "PULocationID"])
    )

    resumen_global_path = DIR_RESUMENES / "resumen_global_semanal_por_dataset_zona.csv"
    conteo_semanal.to_csv(resumen_global_path, index=False)

    print(f"✅ Resumen semanal global guardado en: {resumen_global_path}")
    print(f"✅ Filas finales a renderizar: {len(conteo_semanal)}")

    return conteo_semanal


# ============================================================
# 4. MODO PRUEBA SEMANAL PARA VISUALIZACIÓN
# ============================================================

def generar_datos_prueba_semanal(gdf_zonas, semanas=4, zonas_por_semana=80, seed=42):
    """
    Genera datos simulados por dataset y semana.
    Sirve para validar tu parte de visualización sin descargar archivos reales.
    """
    random.seed(seed)

    zonas_validas = gdf_zonas["LocationID"].dropna().astype(int).tolist()
    datasets = list(DATASETS.keys())

    # Semanas de prueba ficticias
    fechas_inicio = pd.date_range("2024-01-01", periods=semanas, freq="W-MON")

    datos = []
    for dataset in datasets:
        nombre_visual = DATASETS[dataset]["nombre_visual"]

        for week_start in fechas_inicio:
            year = int(week_start.isocalendar().year)
            week = int(week_start.isocalendar().week)

            zonas_muestra = random.sample(
                zonas_validas,
                k=min(zonas_por_semana, len(zonas_validas))
            )

            for zona in zonas_muestra:
                datos.append({
                    "dataset": dataset,
                    "dataset_name": nombre_visual,
                    "year": year,
                    "week": week,
                    "week_start": week_start.date(),
                    "PULocationID": zona,
                    "trip_count": random.randint(100, 60000),
                })

    return pd.DataFrame(datos)


# ============================================================
# 5. RENDERIZADO DE MAPAS SEMANALES
# ============================================================

def calcular_vmax_por_dataset(conteo_semanal):
    """
    Calcula un vmax distinto para cada dataset.

    Esto evita que FHVHV, que suele tener mucho más volumen,
    opaque visualmente a datasets más pequeños como Green Taxi.
    """
    vmax_por_dataset = {}

    for dataset, df_dataset in conteo_semanal.groupby("dataset"):
        valores = df_dataset["trip_count"].dropna()

        if valores.empty:
            vmax = 10
        else:
            vmax = valores.quantile(0.99)
            if pd.isna(vmax) or vmax < 2:
                vmax = 10

        vmax_por_dataset[dataset] = vmax

    return vmax_por_dataset


def guardar_mapa_coropleta_semanal(
    gdf_semana,
    dataset,
    dataset_name,
    year,
    week,
    week_start,
    vmax,
    output_dir,
    modo_test=False,
):
    """
    Genera un mapa de coropletas para un dataset en una semana específica.
    """
    output_dir = Path(output_dir) / dataset
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

    gdf_semana.plot(
        column="trip_count",
        ax=ax,
        cmap=plt.cm.inferno,
        norm=LogNorm(vmin=1, vmax=vmax),
        alpha=0.78,
        edgecolor="#222222",
        linewidth=0.25,
        missing_kwds={"color": "#111111"},
    )

    ctx.add_basemap(
        ax,
        source=ctx.providers.CartoDB.DarkMatter,
        crs=gdf_semana.crs.to_string(),
        attribution=False,
    )

    ax.set_xlim(*NYC_XLIM)
    ax.set_ylim(*NYC_YLIM)
    ax.axis("off")

    etiqueta_test = " | TEST" if modo_test else ""

    titulo = (
        f"UrbanFlow AI - Flujo semanal por plataforma{etiqueta_test}\n"
        f"{dataset_name} | Año {year} | Semana {week:02d} | Inicio: {week_start}"
    )

    plt.text(
        0.04,
        0.94,
        titulo,
        transform=ax.transAxes,
        fontsize=15,
        color="white",
        fontweight="bold",
        bbox=dict(facecolor="#000000", alpha=0.72, edgecolor="none", pad=10),
    )

    nota = (
        "Escala logarítmica por dataset. "
        "Color más intenso = mayor volumen de pickups en la zona."
    )

    plt.text(
        0.04,
        0.04,
        nota,
        transform=ax.transAxes,
        fontsize=9,
        color="#bbbbbb",
        style="italic",
        bbox=dict(facecolor="#000000", alpha=0.45, edgecolor="none", pad=5),
    )

    nombre_archivo = output_dir / f"{dataset}_year_{year}_week_{week:02d}.png"

    plt.savefig(
        nombre_archivo,
        bbox_inches="tight",
        pad_inches=0,
        facecolor="#000000",
    )

    plt.close(fig)
    print(f"🖼️ Mapa generado: {nombre_archivo}")


def renderizar_mapas_semanales(conteo_semanal, gdf_zonas, output_dir, modo_test=False):
    """
    Genera un mapa por cada combinación:
    dataset + año + semana.
    """
    print("🎨 Generando mapas semanales por dataset...")

    conteo_semanal = conteo_semanal.copy()
    conteo_semanal["PULocationID"] = conteo_semanal["PULocationID"].astype(int)

    gdf_zonas = gdf_zonas.copy()
    gdf_zonas["LocationID"] = gdf_zonas["LocationID"].astype(int)

    vmax_por_dataset = calcular_vmax_por_dataset(conteo_semanal)

    grupos = conteo_semanal.groupby(
        ["dataset", "dataset_name", "year", "week", "week_start"],
        sort=True
    )

    total_mapas = grupos.ngroups
    print(f"🧭 Total de mapas a generar: {total_mapas}")

    for (dataset, dataset_name, year, week, week_start), datos_semana in grupos:
        vmax = vmax_por_dataset.get(dataset, 10)

        gdf_semana = gdf_zonas.merge(
            datos_semana,
            left_on="LocationID",
            right_on="PULocationID",
            how="left",
        )

        guardar_mapa_coropleta_semanal(
            gdf_semana=gdf_semana,
            dataset=dataset,
            dataset_name=dataset_name,
            year=int(year),
            week=int(week),
            week_start=week_start,
            vmax=vmax,
            output_dir=output_dir,
            modo_test=modo_test,
        )


# ============================================================
# 6. EJECUCIÓN PRINCIPAL
# ============================================================

def main(modo="test"):
    """
    modo="test":
        Genera datos simulados para 4 semanas y 4 datasets.

    modo="real":
        Descarga y procesa Yellow, Green, FHV y FHVHV de 2024-2025.
    """
    start_total = time.time()

    print("🗺️ Cargando zonas de taxi...")
    gdf_zonas = obtener_shapefile_zonas()

    if modo == "test":
        print("🧪 Ejecutando modo prueba semanal...")
        conteo_semanal = generar_datos_prueba_semanal(
            gdf_zonas,
            semanas=4,
            zonas_por_semana=80,
            seed=42,
        )

        resumen_test = DIR_RESUMENES / "resumen_test_semanal.csv"
        DIR_RESUMENES.mkdir(exist_ok=True)
        conteo_semanal.to_csv(resumen_test, index=False)

        renderizar_mapas_semanales(
            conteo_semanal=conteo_semanal,
            gdf_zonas=gdf_zonas,
            output_dir=DIR_OUTPUT_TEST,
            modo_test=True,
        )

    elif modo == "real":
        print("🏁 Ejecutando modo real semanal 2024-2025...")
        conteo_semanal = procesar_historico_semanal(
            datasets=("yellow", "green", "fhv", "fhvhv"),
            anios=ANIOS,
            meses=MESES,
            guardar_resumenes=True,
        )

        renderizar_mapas_semanales(
            conteo_semanal=conteo_semanal,
            gdf_zonas=gdf_zonas,
            output_dir=DIR_OUTPUT_WEEKLY,
            modo_test=False,
        )

    else:
        raise ValueError("Modo inválido. Usa modo='test' o modo='real'.")

    print(f"\n⏱️ Tiempo total: {time.time() - start_total:.2f} segundos")


if __name__ == "__main__":
    # Para probar la visualización semanal, deja test.
    # Para correr todo el histórico real, cambia a real.
    main(modo="test")
