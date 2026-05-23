import os
import random
import urllib.request
import zipfile
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm

# ==========================================
# 1. DESCARGA DEL SHAPEFILE REAL DE NY
# ==========================================
def obtener_shapefile_zonas():
    os.makedirs('taxi_zones', exist_ok=True)
    shapefile_path = 'taxi_zones/taxi_zones.shp'
    
    if not os.path.exists(shapefile_path):
        print("📥 Descargando Shapefile real de zonas de Nueva York para el test...")
        url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
        zip_path = "taxi_zones/taxi_zones.zip"
        urllib.request.urlretrieve(url, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('./')
        print("✅ Zonas descargadas y extraídas.")
    
    gdf_zonas = gpd.read_file(shapefile_path)
    gdf_zonas = gdf_zonas.to_crs(epsg=3857) # Sistema de coordenadas Web Mercator
    return gdf_zonas

# ==========================================
# 2. FUNCIÓN DE GRAFICACIÓN OPTIMIZADA (ADTECH)
# ==========================================
def guardar_mapa_coropleta_consolidado(gdf_hora, hora, vmax):
    # Creamos un lienzo de alta resolución (DPI 150) apto para presentación ejecutiva
    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
    
    # Dibujamos las zonas usando la paleta 'inferno' (ideal para entornos oscuros)
    gdf_hora.plot(
        column='trip_count',
        ax=ax,
        cmap=plt.cm.inferno,
        norm=LogNorm(vmin=1, vmax=vmax),
        alpha=0.75,
        edgecolor='#222222',
        linewidth=0.3,
        missing_kwds={'color': '#111111'} # Zonas sin viajes en gris muy oscuro
    )
    
    # Añadimos el mapa base oscuro de CartoDB
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, crs=gdf_hora.crs.to_string(), attribution=False)
    
    # Encuadre extendido para abarcar todo Nueva York (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
    ax.set_xlim(-8270000, -8200000)
    ax.set_ylim(4930000, 5010000)
    ax.axis('off')
    
    # Título corporativo para Coca-Cola / UrbanFlow AI
    plt.text(0.04, 0.94, f'UrbanFlow AI - Flujo Vehicular Consolidado\nHora Promedio: {hora:02d}:00', 
             transform=ax.transAxes, fontsize=16, color='white', fontweight='bold', 
             bbox=dict(facecolor='#000000', alpha=0.7, edgecolor='none', pad=10))
    
    # Nota explicativa de los datos de simulación
    plt.text(0.04, 0.04, '*Test Mode: Escala logarítmica basada en simulación de flujos masivos', 
             transform=ax.transAxes, fontsize=9, color='#aaaaaa', style='italic')
    
    # Guardamos el resultado en la carpeta de salida
    os.makedirs('output_test', exist_ok=True)
    nombre_archivo = f"output_test/test_flujo_hora_{hora:02d}.png"
    plt.savefig(nombre_archivo, bbox_inches='tight', pad_inches=0, facecolor='#000000')
    plt.close(fig)
    print(f"🖼️ Mapa generado exitosamente: {nombre_archivo}")

# ==========================================
# 3. EJECUCIÓN DEL TEST
# ==========================================
if __name__ == '__main__':
    print("🚀 Iniciando entorno de pruebas de graficación...")
    
    # Cargamos el mapa base real para conocer los IDs de las zonas válidas (LocationID del 1 al 263 aprox)
    gdf_zonas = obtener_shapefile_zonas()
    lista_zonas_validas = gdf_zonas['LocationID'].tolist()
    
    # --- GENERACIÓN DE 10 DATOS ALEATORIOS CONTROLADOS ---
    # Simulamos la estructura final que saldría del Pipeline optimizado:
    # Columnas: ['hour', 'PULocationID', 'trip_count']
    print("\n📊 Generando 10 registros aleatorios de prueba...")
    
    datos_prueba = []
    for _ in range(10):
        registro = {
            'hour': random.randint(0, 23),                     # Hora aleatoria del día
            'PULocationID': random.choice(lista_zonas_validas), # Una zona real de NY al azar
            'trip_count': random.randint(50, 15000)            # Volúmenes masivos simulando Uber/Taxis
        }
        datos_prueba.append(registro)
        
    conteo_viajes_test = pd.DataFrame(datos_prueba)
    
    # Imprimimos la tabla en consola para verificar los datos de prueba antes de pintar
    print("\n--- TABLA DE DATOS GENERADA ---")
    print(conteo_viajes_test.to_string(index=False))
    print("--------------------------------\n")
    
    # Establecemos un vmax global fijo para el test (el conteo máximo generado)
    vmax_global = conteo_viajes_test['trip_count'].max()
    
    print("🎨 Procesando e integrando datos al mapa...")
    # Ejecutamos el ciclo de renderizado solo para las horas donde nuestros 10 datos ficticios tienen presencia
    horas_con_datos = conteo_viajes_test['hour'].unique()
    
    for hora in horas_con_datos:
        # 1. Filtramos los datos de la hora en curso
        datos_hora = conteo_viajes_test[conteo_viajes_test['hour'] == hora]
        
        # 2. Hacemos el Merge (JOIN) con el mapa geográfico
        gdf_hora = gdf_zonas.merge(datos_hora, left_on='LocationID', right_on='PULocationID', how='left')
        
        # 3. Graficamos e imprimimos el reporte
        guardar_mapa_coropleta_consolidado(gdf_hora, hora, vmax_global)
        
    print("\n✅ ¡Test finalizado! Revisa la carpeta 'output_test' para ver los mapas generados.")