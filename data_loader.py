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

    # Cargar archivos de consolidado
    for ruta in rutas_consolidado:
        if Path(ruta).exists():
            print(f"📂 Cargando: {ruta}")
            df = pd.read_csv(ruta, dtype={'altas': 'float32', 'ingresos': 'float32'}, low_memory=False)
            df.columns = [normalize_column_name(c) for c in df.columns]
            if 'campana_final' in df.columns:
                df['campana_final'] = df['campana_final'].astype(str).str.strip().str.upper()
            else:
                print(f"⚠️ Advertencia: 'campana_final' no encontrada en {ruta}")
            consolidados.append(df)
        else:
            print(f"❌ Archivo no encontrado: {ruta}")

    # Cargar archivos de metas
    for ruta in rutas_metas:
        if Path(ruta).exists():
            print(f"📂 Cargando: {ruta}")
            df = pd.read_csv(ruta, dtype={'altas': 'float32', 'ingresos': 'float32'}, low_memory=False)
            df.columns = [normalize_column_name(c) for c in df.columns]
            if 'campana_final' in df.columns:
                df['campana_final'] = df['campana_final'].astype(str).str.strip().str.upper()
            else:
                print(f"⚠️ Advertencia: 'campana_final' no encontrada en {ruta}")
            metas_list.append(df)
        else:
            print(f"❌ Archivo no encontrado: {ruta}")

    # Combinar DataFrames
    df_consolidado = pd.concat(consolidados, ignore_index=True) if consolidados else pd.DataFrame()
    df_metas = pd.concat(metas_list, ignore_index=True) if metas_list else pd.DataFrame()

    return df_consolidado, df_metas