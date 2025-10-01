import pandas as pd
from pathlib import Path
import unicodedata

def normalize_column_name(name):
    """
    Normaliza nombres de columnas: quita acentos, espacios, y convierte a minúsculas con guiones bajos.
    Ej: "CAMPAÑA FINAL" → "campana_final"
    """
    if not isinstance(name, str):
        return name
    # Quitar acentos
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    # Reemplazar espacios por guiones bajos y convertir a minúsculas
    return name.strip().lower().replace(' ', '_')

def cargar_datos():
    """
    Carga y combina datos de los 4 archivos CSV:
    - Consolidado2024.csv
    - Consolidado2025.csv
    - MetasConsolidado2024.csv
    - MetasConsolidado2025.csv
    
    Returns:
        tuple: (df_consolidado, df_metas) - DataFrames combinados
    """
    # Rutas de los archivos CSV
    rutas_consolidado = [
        "Consolidado2024.csv",
        "Consolidado2025.csv"
    ]
    rutas_metas = [
        "MetasConsolidado2024.csv",
        "MetasConsolidado2025.csv"
    ]

    consolidados = []
    metas_list = []

    print("📁 Iniciando carga de archivos CSV...")

    # Cargar archivos de consolidado
    for ruta in rutas_consolidado:
        if Path(ruta).exists():
            print(f"📂 Cargando: {ruta}")
            try:
                df = pd.read_csv(
                    ruta, 
                    dtype={'altas': 'float32', 'ingresos': 'float32'}, 
                    low_memory=False,
                    encoding='utf-8'
                )
                df.columns = [normalize_column_name(c) for c in df.columns]
                
                # Validar columnas críticas
                if 'campana_final' in df.columns:
                    df['campana_final'] = df['campana_final'].astype(str).str.strip().str.upper()
                else:
                    print(f"⚠️ Advertencia: 'campana_final' no encontrada en {ruta}")
                
                # Verificar columnas numéricas
                if 'altas' not in df.columns:
                    print(f"⚠️ Advertencia: 'altas' no encontrada en {ruta}")
                if 'ingresos' not in df.columns:
                    print(f"⚠️ Advertencia: 'ingresos' no encontrada en {ruta}")
                
                consolidados.append(df)
                print(f"   ✅ {ruta} cargado - {len(df)} filas")
                
            except Exception as e:
                print(f"❌ Error cargando {ruta}: {e}")
        else:
            print(f"❌ Archivo no encontrado: {ruta}")

    # Cargar archivos de metas
    for ruta in rutas_metas:
        if Path(ruta).exists():
            print(f"📂 Cargando: {ruta}")
            try:
                df = pd.read_csv(
                    ruta, 
                    dtype={'altas': 'float32', 'ingresos': 'float32'}, 
                    low_memory=False,
                    encoding='utf-8'
                )
                df.columns = [normalize_column_name(c) for c in df.columns]
                
                if 'campana_final' in df.columns:
                    df['campana_final'] = df['campana_final'].astype(str).str.strip().str.upper()
                else:
                    print(f"⚠️ Advertencia: 'campana_final' no encontrada en {ruta}")
                
                metas_list.append(df)
                print(f"   ✅ {ruta} cargado - {len(df)} filas")
                
            except Exception as e:
                print(f"❌ Error cargando {ruta}: {e}")
        else:
            print(f"❌ Archivo no encontrado: {ruta}")

    # Combinar DataFrames
    df_consolidado = pd.concat(consolidados, ignore_index=True) if consolidados else pd.DataFrame()
    df_metas = pd.concat(metas_list, ignore_index=True) if metas_list else pd.DataFrame()

    # VALIDACIÓN CRÍTICA - Verificar que se cargaron datos
    if df_consolidado.empty:
        raise Exception("❌ No se pudieron cargar los datos de consolidado. Verifica que los archivos CSV existan.")
    if df_metas.empty:
        raise Exception("❌ No se pudieron cargar los datos de metas. Verifica que los archivos CSV existan.")

    # Informe final de carga
    print(f"✅ CARGA COMPLETADA:")
    print(f"   - Consolidado: {len(df_consolidado)} registros totales")
    print(f"   - Metas: {len(df_metas)} registros totales")
    
    # Mostrar columnas disponibles para debugging
    print(f"   - Columnas en consolidado: {list(df_consolidado.columns)}")
    print(f"   - Columnas en metas: {list(df_metas.columns)}")

    return df_consolidado, df_metas

# Función auxiliar para debugging
def mostrar_estadisticas(df_consolidado, df_metas):
    """Muestra estadísticas básicas de los datos cargados"""
    print("\n📊 ESTADÍSTICAS DE DATOS CARGADOS:")
    print(f"Consolidado:")
    print(f"  - Total registros: {len(df_consolidado)}")
    print(f"  - Columnas: {list(df_consolidado.columns)}")
    if not df_consolidado.empty:
        print(f"  - Rango de fechas: {df_consolidado['mes'].min()} a {df_consolidado['mes'].max()}")
        print(f"  - Aliados únicos: {df_consolidado['campana_final'].nunique()}")
    
    print(f"Metas:")
    print(f"  - Total registros: {len(df_metas)}")
    print(f"  - Columnas: {list(df_metas.columns)}")
    if not df_metas.empty:
        print(f"  - Rango de fechas: {df_metas['mes'].min()} a {df_metas['mes'].max()}")