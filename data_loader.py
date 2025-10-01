import pandas as pd
from pathlib import Path
import unicodedata

def normalize_column_name(name):
    if not isinstance(name, str):
        return name
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return name.strip().lower().replace(' ', '_')

def cargar_datos():
    """
    VERSIÓN OPTIMIZADA - Solo 2025 para máxima estabilidad en Render
    """
    print("🚀 INICIANDO CARGA OPTIMIZADA (solo 2025)...")
    
    try:
        # SOLO columnas esenciales para ahorrar memoria
        columnas_esenciales = ['campana_final', 'altas', 'ingresos', 'mes']
        
        consolidados = []
        metas_list = []

        # 📊 CARGAR SOLO 2025 - CONSOLIDADO
        if Path("Consolidado2025.csv").exists():
            print("📂 Cargando Consolidado2025.csv...")
            df_2025 = pd.read_csv(
                "Consolidado2025.csv",
                usecols=columnas_esenciales,
                dtype={
                    'altas': 'float32', 
                    'ingresos': 'float32',
                    'campana_final': 'category'  # ✅ OPTIMIZA MEMORIA
                },
                low_memory=True
            )
            df_2025.columns = [normalize_column_name(c) for c in df_2025.columns]
            consolidados.append(df_2025)
            print(f"✅ Consolidado2025: {len(df_2025)} filas cargadas")

        # 🎯 CARGAR SOLO 2025 - METAS
        if Path("MetasConsolidado2025.csv").exists():
            print("📂 Cargando MetasConsolidado2025.csv...")
            df_metas_2025 = pd.read_csv(
                "MetasConsolidado2025.csv",
                usecols=columnas_esenciales,
                dtype={
                    'altas': 'float32',
                    'ingresos': 'float32', 
                    'campana_final': 'category'
                },
                low_memory=True
            )
            df_metas_2025.columns = [normalize_column_name(c) for c in df_metas_2025.columns]
            metas_list.append(df_metas_2025)
            print(f"✅ Metas2025: {len(df_metas_2025)} filas cargadas")

        # Combinar datos (en este caso solo habrá uno de cada)
        df_consolidado = pd.concat(consolidados, ignore_index=True) if consolidados else pd.DataFrame()
        df_metas = pd.concat(metas_list, ignore_index=True) if metas_list else pd.DataFrame()

        # 📈 ESTADÍSTICAS FINALES
        print(f"\n🎉 CARGA 2025 COMPLETADA:")
        print(f"   - Consolidado: {len(df_consolidado)} registros")
        print(f"   - Metas: {len(df_metas)} registros")
        
        if not df_consolidado.empty:
            print(f"   - Aliados únicos: {df_consolidado['campana_final'].nunique()}")
            print(f"   - Total altas: {df_consolidado['altas'].sum():,.0f}")
            print(f"   - Total ingresos: S/ {df_consolidado['ingresos'].sum():,.2f}")

        return df_consolidado, df_metas

    except Exception as e:
        print(f"❌ ERROR en carga: {e}")
        # Retornar DataFrames vacíos para que la app no crashee
        return pd.DataFrame(), pd.DataFrame()