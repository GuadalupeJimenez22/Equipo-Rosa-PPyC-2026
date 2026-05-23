import argparse
import json
import random
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import contextily as ctx
import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LogNorm


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

ANIOS = [2024, 2025]
MESES = list(range(1, 13))

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
DIR_DATA = Path("data")
DIR_TEMP = Path("tmp_downloads")
DIR_RESUMENES = Path("resumenes_weekly")
DIR_OUTPUT = Path("output_weekly")
DIR_OUTPUT_TEST = Path("output_weekly_test")

SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
SHAPEFILE_PATH = DIR_TAXI_ZONES / "taxi_zones.shp"

NYC_XLIM = (-8270000, -8200000)
NYC_YLIM = (4930000, 5010000)


# ============================================================
# 1. SHAPEFILE
# ============================================================

def obtener_shapefile_zonas():
    """
    Descarga y carga el shapefile oficial de zonas de taxi de NYC.
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
    columnas_existentes = [
        c for c in columnas_necesarias
        if c in gdf_zonas.columns
    ]

    gdf_zonas = gdf_zonas[columnas_existentes].copy()
    gdf_zonas["LocationID"] = gdf_zonas["LocationID"].astype(int)

    return gdf_zonas


# ============================================================
# 2. UTILIDADES PARA PARQUET
# ============================================================

def obtener_columnas_parquet(con, parquet_path):
    """
    Lee únicamente el esquema del parquet.
    No carga todo el archivo a memoria.
    """
    parquet_path = Path(parquet_path).as_posix()
    query = f"DESCRIBE SELECT * FROM read_parquet('{parquet_path}')"
    columnas = con.query(query).df()["column_name"].tolist()
    return columnas


def elegir_columna(columnas_disponibles, candidatos, nombre_logico):
    """
    Elige la primera columna candidata que exista.
    Se hace ignorando mayúsculas/minúsculas.
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


def ruta_local_parquet(dataset, anio, mes):
    """
    Busca primero en:
    data/<dataset>/<dataset>_tripdata_AAAA-MM.parquet

    y después en:
    data/<dataset>_tripdata_AAAA-MM.parquet
    """
    nombre = f"{dataset}_tripdata_{anio}-{mes:02d}.parquet"

    posibles_rutas = [
        DIR_DATA / dataset / nombre,
        DIR_DATA / nombre,
    ]

    for ruta in posibles_rutas:
        if ruta.exists():
            return ruta

    return None


def descargar_parquet(dataset, anio, mes):
    """
    Descarga temporalmente un archivo Parquet si no existe localmente.
    """
    config = DATASETS[dataset]
    DIR_TEMP.mkdir(exist_ok=True)

    url = config["url_pattern"].format(anio=anio, mes=mes)
    destino = DIR_TEMP / f"{dataset}_tripdata_{anio}-{mes:02d}.parquet"

    print(f"📥 Descargando {dataset.upper()} {anio}-{mes:02d}...")

    try:
        urllib.request.urlretrieve(url, destino)
        return destino

    except urllib.error.HTTPError as e:
        print(f"⚠️ No disponible: {dataset} {anio}-{mes:02d}. HTTP {e.code}")
        return None

    except Exception as e:
        print(f"❌ Error descargando {dataset} {anio}-{mes:02d}: {e}")
        return None


# ============================================================
# 3. PROCESAMIENTO SEMANAL CON DUCKDB
# ============================================================

def procesar_parquet_semanal(con, parquet_path, dataset):
    """
    Convierte un Parquet grande en un resumen pequeño:

    dataset
    dataset_name
    year
    week
    week_start
    PULocationID
    trip_count

    Aquí se consolida por semana, no por hora.
    """
    config = DATASETS[dataset]

    columnas = obtener_columnas_parquet(con, parquet_path)

    datetime_col = elegir_columna(
        columnas,
        config["datetime_candidates"],
        nombre_logico="fecha/hora de pickup",
    )

    pickup_col = elegir_columna(
        columnas,
        config["pickup_candidates"],
        nombre_logico="zona de pickup",
    )

    parquet_sql = Path(parquet_path).as_posix().replace("'", "''")

    query = f"""
        SELECT
            '{dataset}' AS dataset,
            '{config["nombre_visual"]}' AS dataset_name,
            CAST(strftime({datetime_col}, '%G') AS INT) AS year,
            CAST(strftime({datetime_col}, '%V') AS INT) AS week,
            DATE_TRUNC('week', {datetime_col})::DATE AS week_start,
            TRY_CAST({pickup_col} AS INT) AS PULocationID,
            COUNT(*)::BIGINT AS trip_count
        FROM read_parquet('{parquet_sql}')
        WHERE
            {datetime_col} IS NOT NULL
            AND TRY_CAST({pickup_col} AS INT) IS NOT NULL
            AND TRY_CAST({pickup_col} AS INT) > 0
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
    usar_local=True,
    borrar_temporales=True,
):
    """
    Procesa todos los meses de 2024 y 2025.

    Si existen archivos locales, los usa.
    Si no existen, intenta descargarlos desde TLC.
    """
    DIR_RESUMENES.mkdir(exist_ok=True)
    con = duckdb.connect()

    resumenes = []
    total_planeados = len(datasets) * len(anios) * len(meses)
    total_procesados = 0

    print("🚀 Iniciando consolidación semanal 2024/2025...")
    print(f"📦 Archivos planeados: {total_planeados}")

    for dataset in datasets:
        if dataset not in DATASETS:
            print(f"⚠️ Dataset desconocido: {dataset}. Se omite.")
            continue

        for anio in anios:
            for mes in meses:
                parquet_path = None
                es_temporal = False

                if usar_local:
                    parquet_path = ruta_local_parquet(dataset, anio, mes)

                if parquet_path is None:
                    parquet_path = descargar_parquet(dataset, anio, mes)
                    es_temporal = True

                if parquet_path is None:
                    continue

                print(f"⚙️ Procesando {dataset.upper()} {anio}-{mes:02d}: {parquet_path}")

                try:
                    resumen_mes = procesar_parquet_semanal(
                        con=con,
                        parquet_path=parquet_path,
                        dataset=dataset,
                    )

                    resumenes.append(resumen_mes)
                    total_procesados += 1

                    if guardar_resumenes:
                        salida_mes = DIR_RESUMENES / f"resumen_{dataset}_{anio}_{mes:02d}.csv"
                        resumen_mes.to_csv(salida_mes, index=False)

                    print(f"✅ Filas resumen: {len(resumen_mes)}")

                except Exception as e:
                    print(f"❌ Error procesando {dataset} {anio}-{mes:02d}: {e}")

                finally:
                    if es_temporal and borrar_temporales and parquet_path.exists():
                        parquet_path.unlink()

    if not resumenes:
        raise RuntimeError(
            "No se generó ningún resumen. "
            "Revisa conexión, rutas o disponibilidad de archivos."
        )

    print(f"\n🔄 Consolidando {total_procesados} archivos procesados...")

    df = pd.concat(resumenes, ignore_index=True)

    conteo_semanal = (
        df.groupby(
            [
                "dataset",
                "dataset_name",
                "year",
                "week",
                "week_start",
                "PULocationID",
            ],
            as_index=False,
        )["trip_count"]
        .sum()
        .sort_values(["dataset", "year", "week", "PULocationID"])
    )

    salida_global = DIR_RESUMENES / "resumen_global_2024_2025_semanal_por_dataset_zona.csv"
    conteo_semanal.to_csv(salida_global, index=False)

    print(f"✅ Resumen global guardado en: {salida_global}")
    print(f"✅ Filas consolidadas: {len(conteo_semanal)}")

    return conteo_semanal


# ============================================================
# 4. MODO TEST 2024/2025 COMPLETO
# ============================================================

def generar_datos_prueba_2024_2025(gdf_zonas, zonas_por_semana=80, seed=42):
    """
    Genera datos simulados para todas las semanas de 2024 y 2025.
    Esto sirve para probar el HTML sin descargar los Parquet reales.
    """
    random.seed(seed)

    zonas_validas = (
        gdf_zonas["LocationID"]
        .dropna()
        .astype(int)
        .tolist()
    )

    fechas_inicio = pd.date_range(
        "2024-01-01",
        "2025-12-31",
        freq="W-MON",
    )

    datos = []

    for dataset, config in DATASETS.items():
        for week_start in fechas_inicio:
            iso = week_start.isocalendar()
            year = int(iso.year)
            week = int(iso.week)

            if year not in [2024, 2025]:
                continue

            zonas_muestra = random.sample(
                zonas_validas,
                k=min(zonas_por_semana, len(zonas_validas)),
            )

            for zona in zonas_muestra:
                datos.append(
                    {
                        "dataset": dataset,
                        "dataset_name": config["nombre_visual"],
                        "year": year,
                        "week": week,
                        "week_start": week_start.date(),
                        "PULocationID": zona,
                        "trip_count": random.randint(100, 60000),
                    }
                )

    return pd.DataFrame(datos)


# ============================================================
# 5. RENDERIZADO DE MAPAS
# ============================================================

def calcular_vmax_por_dataset(conteo_semanal):
    """
    Calcula un vmax por dataset para que FHVHV no opaque a Green o Yellow.
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
    Genera un PNG por dataset + año + semana.
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
    total_semana = int(gdf_semana["trip_count"].fillna(0).sum())

    titulo = (
        f"UrbanFlow AI - Afluencia semanal por plataforma{etiqueta_test}\n"
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
        f"Afluencia semanal consolidada: {total_semana:,} pickups | "
        "Escala logarítmica por dataset"
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

    return nombre_archivo


def renderizar_mapas_semanales(
    conteo_semanal,
    gdf_zonas,
    output_dir,
    modo_test=False,
):
    """
    Genera un mapa por cada combinación:
    dataset + año + semana.
    """
    print("🎨 Generando mapas semanales por dataset...")

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    conteo_semanal = conteo_semanal.copy()
    conteo_semanal["PULocationID"] = conteo_semanal["PULocationID"].astype(int)

    gdf_zonas = gdf_zonas.copy()
    gdf_zonas["LocationID"] = gdf_zonas["LocationID"].astype(int)

    vmax_por_dataset = calcular_vmax_por_dataset(conteo_semanal)

    grupos = conteo_semanal.groupby(
        ["dataset", "dataset_name", "year", "week", "week_start"],
        sort=True,
    )

    print(f"🧭 Total de mapas a generar: {grupos.ngroups}")

    manifest_items = []

    for (dataset, dataset_name, year, week, week_start), datos_semana in grupos:
        vmax = vmax_por_dataset.get(dataset, 10)

        gdf_semana = gdf_zonas.merge(
            datos_semana,
            left_on="LocationID",
            right_on="PULocationID",
            how="left",
        )

        ruta_png = guardar_mapa_coropleta_semanal(
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

        manifest_items.append(
            {
                "dataset": dataset,
                "dataset_name": dataset_name,
                "year": int(year),
                "week": int(week),
                "week_start": str(week_start),
                "trip_count": int(datos_semana["trip_count"].sum()),
                "image": ruta_png.as_posix(),
            }
        )

    guardar_manifest(manifest_items, output_dir)

    return manifest_items


# ============================================================
# 6. MANIFEST PARA HTML
# ============================================================

def guardar_manifest(manifest_items, output_dir):
    """
    Guarda un manifest.json para que el HTML sepa qué imágenes existen.
    """
    output_dir = Path(output_dir)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "items": manifest_items,
    }

    manifest_path = output_dir / "manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"🧾 Manifest guardado en: {manifest_path}")


# ============================================================
# 7. MAIN
# ============================================================

def main(modo="real"):
    """
    modo="test":
        Genera semanas simuladas para 2024 y 2025 completos.

    modo="real":
        Descarga o usa archivos reales de 2024 y 2025 completos.
    """
    start_total = time.time()

    print("🗺️ Cargando zonas de taxi...")
    gdf_zonas = obtener_shapefile_zonas()

    if modo == "test":
        print("🧪 Ejecutando modo prueba 2024/2025 completo...")

        conteo_semanal = generar_datos_prueba_2024_2025(
            gdf_zonas,
            zonas_por_semana=80,
            seed=42,
        )

        DIR_RESUMENES.mkdir(exist_ok=True)

        resumen_test = DIR_RESUMENES / "resumen_test_2024_2025_semanal.csv"
        conteo_semanal.to_csv(resumen_test, index=False)

        renderizar_mapas_semanales(
            conteo_semanal=conteo_semanal,
            gdf_zonas=gdf_zonas,
            output_dir=DIR_OUTPUT_TEST,
            modo_test=True,
        )

    elif modo == "real":
        print("🏁 Ejecutando modo real 2024/2025 completo...")

        conteo_semanal = procesar_historico_semanal(
            datasets=("yellow", "green", "fhv", "fhvhv"),
            anios=ANIOS,
            meses=MESES,
            guardar_resumenes=True,
            usar_local=True,
            borrar_temporales=True,
        )

        renderizar_mapas_semanales(
            conteo_semanal=conteo_semanal,
            gdf_zonas=gdf_zonas,
            output_dir=DIR_OUTPUT,
            modo_test=False,
        )

    else:
        raise ValueError("Modo inválido. Usa modo='test' o modo='real'.")

    print(f"\n⏱️ Tiempo total: {time.time() - start_total:.2f} segundos")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--modo",
        choices=["test", "real"],
        default="real",
        help="test genera datos simulados 2024/2025; real procesa Parquet reales 2024/2025.",
    )

    args = parser.parse_args()

    main(modo=args.modo)