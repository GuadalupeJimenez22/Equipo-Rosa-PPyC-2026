import os
import time
import urllib.request
import urllib.error
import zipfile
import threading
import multiprocessing
import queue
import signal
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm
import duckdb
from sqlalchemy import create_engine, text
from datetime import date, timedelta

# ==========================================
# CONEXIÓN A BASE DE DATOS
# ==========================================
def get_connection():
    return create_engine(
        "postgresql+psycopg2://postgres:postgres@localhost:5450/ppyc_db",
        connect_args={"options": "-csearch_path=urbanflow,public"}
    )

# ==========================================
# CARGA DE ZONAS
# ==========================================
def cargar_zonas(engine):
    print("🗺️ Cargando zonas en la base de datos...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE urbanflow.zones_geometry RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE urbanflow.zones RESTART IDENTITY CASCADE"))
    try:
        df_lookup = pd.read_csv(
            "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
        )
        df_lookup.columns = [c.lower() for c in df_lookup.columns]
        df_lookup.to_sql('zones', engine, schema='urbanflow',
                         if_exists='append', index=False, method='multi')
        print(f"✅ {len(df_lookup)} zonas insertadas en zones")
    except Exception as e:
        print(f"⚠️ Error cargando zones: {e}")

    shapefile_path = 'taxi_zones/taxi_zones.shp'
    if os.path.exists(shapefile_path):
        try:
            gdf = gpd.read_file(shapefile_path)
            gdf = gdf.to_crs(epsg=4326)
            gdf['wkb'] = gdf['geometry'].apply(lambda x: x.wkb_hex)
            with engine.begin() as conn:
                for _, row in gdf.iterrows():
                    conn.execute(text("""
                        INSERT INTO zones_geometry (LocationID, geometry)
                        VALUES (:loc, ST_SetSRID(ST_GeomFromWKB(:wkb), 4326))
                        ON CONFLICT (LocationID) DO NOTHING
                    """), {"loc": row["LocationID"], "wkb": row["wkb"]})
            print(f"✅ {len(gdf)} geometrías insertadas en zones_geometry")
        except Exception as e:
            print(f"⚠️ Error cargando geometrías: {e}")

# ==========================================
# CARGA DEL CALENDARIO
# ==========================================
def cargar_calendario(engine):
    print("📅 Cargando calendario en la base de datos...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE urbanflow.trip_statistics RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE urbanflow.calendar RESTART IDENTITY CASCADE"))
    registros = []
    for anio in [2024, 2025]:
        d = date(anio, 1, 1)
        while d.year == anio:
            registros.append({
                "date": d,
                "year": d.year,
                "month": d.month,
                "day": d.day,
                "is_weekend": d.weekday() >= 5
            })
            d += timedelta(days=1)
    df_cal = pd.DataFrame(registros)
    df_cal.to_sql('calendar', engine, schema='urbanflow',
                  if_exists='append', index=False, method='multi')
    print(f"✅ {len(df_cal)} días insertados en calendar")

# ==========================================
# CARGA DE ESTADÍSTICAS DE VIAJES
# ==========================================
def cargar_trip_statistics(engine, conteo_viajes, fecha):
    with engine.begin() as conn:
        data = [
            {"loc": int(row["PULocationID"]), "date": fecha,
             "hour": int(row["hour"]), "count": int(row["trip_count"])}
            for _, row in conteo_viajes.iterrows()
        ]
        conn.execute(text("""
            INSERT INTO trip_statistics (LocationID, date, hour, trip_count)
            VALUES (:loc, :date, :hour, :count)
            ON CONFLICT (LocationID, date, hour) DO UPDATE
            SET trip_count = trip_statistics.trip_count + EXCLUDED.trip_count
        """), data)
    print(f"✅ {len(conteo_viajes)} filas insertadas/acumuladas en trip_statistics")

# ==========================================
# DESCARGA DEL SHAPEFILE DE ZONAS
# ==========================================
def obtener_shapefile_zonas():
    os.makedirs('taxi_zones', exist_ok=True)
    shapefile_path = 'taxi_zones/taxi_zones.shp'

    if not os.path.exists(shapefile_path):
        print("📥 Descargando Shapefile de zonas de Nueva York...")
        url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
        zip_path = "taxi_zones/taxi_zones.zip"
        try:
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('./taxi_zones/')
            print("✅ Zonas descargadas y extraídas.")
        except Exception as e:
            print(f"❌ No se pudo descargar el shapefile: {e}")
            print("💡 Usa una VPN con IP de EE.UU. o configura HTTP_PROXY")
            exit()

    gdf_zonas = gpd.read_file(shapefile_path)
    gdf_zonas = gdf_zonas.to_crs(epsg=3857)
    return gdf_zonas

# ==========================================
# HILO DE DESCARGA (I/O bound)
# ==========================================
def hilo_descarga(cola_descargas, anio, mes):
    archivo_temp = f"temp_{anio}_{mes:02d}.parquet"
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{anio}-{mes:02d}.parquet"
    try:
        urllib.request.urlretrieve(url, archivo_temp)
        cola_descargas.put((anio, mes, archivo_temp))
    except urllib.error.HTTPError:
        pass
    except Exception:
        if os.path.exists(archivo_temp):
            os.remove(archivo_temp)

# ==========================================
# PROCESO WORKER (CPU bound - DuckDB)
# ==========================================
def worker_proceso(cola_in, cola_out, evento_fin):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    while True:
        try:
            item = cola_in.get(timeout=1)
        except queue.Empty:
            if evento_fin.is_set():
                break
            continue
        if item is None:
            break
        anio, mes, archivo_temp = item
        try:
            con = duckdb.connect()
            df = con.query(f"""
                SELECT EXTRACT(HOUR FROM tpep_pickup_datetime)::INT as hour,
                       PULocationID, COUNT(*) as trip_count
                FROM read_parquet('{archivo_temp}')
                GROUP BY hour, PULocationID
            """).df()
            con.close()
            os.remove(archivo_temp)
            cola_out.put((df, anio, mes))
        except Exception:
            if os.path.exists(archivo_temp):
                os.remove(archivo_temp)

# ==========================================
# RENDERIZADO DEL MAPA DE COROPLETAS
# ==========================================
def guardar_mapa_coropleta(gdf_hora, hora, vmax):
    fig, ax = plt.subplots(figsize=(12, 12), dpi=120)
    gdf_hora.plot(
        column='trip_count',
        ax=ax,
        cmap=plt.cm.hot,
        norm=LogNorm(vmin=1, vmax=vmax),
        alpha=0.8,
        edgecolor='black',
        linewidth=0.3,
        missing_kwds={'color': 'none'}
    )
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter,
                    crs=gdf_hora.crs.to_string(), attribution=False)
    ax.set_xlim(-8250000, -8210000)
    ax.set_ylim(4960000, 4995000)
    ax.axis('off')
    plt.text(0.05, 0.95, f'Hora: {hora:02d}:00', transform=ax.transAxes,
             fontsize=24, color='white', fontweight='bold',
             bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))
    nombre_archivo = f"output/zonas_hora_{hora:02d}.png"
    plt.savefig(nombre_archivo, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close(fig)
    print(f"Guardado mapa de zonas: {nombre_archivo}")

# ==========================================
# PROCESAMIENTO PRINCIPAL
# ==========================================
if __name__ == '__main__':
    os.makedirs('output', exist_ok=True)
    start_total = time.time()

    engine = get_connection()

    cargar_zonas(engine)
    cargar_calendario(engine)

    print("🚀 Iniciando pipeline con threading + multiprocessing...")

    n_procesos = 4
    cola_descargas = multiprocessing.Queue()
    cola_resultados = multiprocessing.Queue()
    evento_fin = multiprocessing.Event()

    procesos = []
    for _ in range(n_procesos):
        p = multiprocessing.Process(target=worker_proceso,
                                    args=(cola_descargas, cola_resultados, evento_fin))
        p.start()
        procesos.append(p)

    hilos = []
    for anio in [2024, 2025]:
        for mes in range(1, 13):
            h = threading.Thread(target=hilo_descarga,
                                 args=(cola_descargas, anio, mes))
            h.start()
            hilos.append(h)

    for h in hilos:
        h.join()

    evento_fin.set()

    for _ in procesos:
        cola_descargas.put(None)

    for p in procesos:
        p.join()

    lista_resumenes = []
    exitos = 0
    while not cola_resultados.empty():
        try:
            df, anio, mes = cola_resultados.get_nowait()
            lista_resumenes.append((df, anio, mes))
            exitos += 1
        except queue.Empty:
            break

    total = 24
    fallos = total - exitos
    print(f"✅ {exitos} meses procesados correctamente")
    if fallos > 0:
        print(f"⚠️ {fallos} meses no disponibles")

    if not lista_resumenes:
        print("❌ No se pudo descargar ningún archivo. Verifica tu conexión a internet.")
        exit()

    print("🔄 Consolidando todos los datos...")
    dfs = [item[0] for item in lista_resumenes]
    df_consolidado = pd.concat(dfs, ignore_index=True)
    conteo_viajes = df_consolidado.groupby(
        ['hour', 'PULocationID']
    )['trip_count'].sum().reset_index()
    print(f"✅ Agrupación total. Filas: {len(conteo_viajes)}")

    cargar_trip_statistics(engine, conteo_viajes, "2024-01-01")

    print("🗺️ Cargando Shapefile de zonas...")
    gdf_zonas = obtener_shapefile_zonas()

    vmax_global = conteo_viajes['trip_count'].quantile(0.99)
    if vmax_global < 2:
        vmax_global = 10

    print("🎨 Generando mapas de calor por zonas...")
    start_render = time.time()

    for hora in range(24):
        datos_hora = conteo_viajes[conteo_viajes['hour'] == hora]
        gdf_hora = gdf_zonas.merge(
            datos_hora, left_on='LocationID', right_on='PULocationID', how='left'
        )
        guardar_mapa_coropleta(gdf_hora, hora, vmax_global)

    print(f"Tiempo de renderizado: {time.time() - start_render:.2f} segundos")
    print(f"⏱️ TIEMPO TOTAL: {time.time() - start_total:.2f} segundos")
