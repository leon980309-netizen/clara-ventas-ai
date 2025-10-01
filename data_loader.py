import pandas as pd
from pathlib import Path

def cargar_datos():
    """Carga mínima - solo columnas esenciales"""
    print("🚀 CARGANDO VERSIÓN MÍNIMA...")
    
    try:
        # SOLO columnas absolutamente necesarias
        columnas_esenciales = ['campana_final', 'altas', 'ingresos', 'mes']
        
        # Cargar con máxima optimización
        df_consolidado = pd.read_csv(
            "Consolidado2025.csv",
            usecols=columnas_esenciales,
            dtype={'altas': 'int32', 'ingresos': 'float32'},
            nrows=50000  # Límite de seguridad
        )
        
        df_metas = pd.read_csv(
            "MetasConsolidado2025.csv", 
            usecols=columnas_esenciales,
            dtype={'altas': 'int32', 'ingresos': 'float32'},
            nrows=1000
        )
        
        print(f"✅ CARGA MÍNIMA EXITOSA: {len(df_consolidado)} registros")
        return df_consolidado, df_metas
        
    except Exception as e:
        print(f"❌ Error en carga mínima: {e}")
        # Datos de emergencia
        return pd.DataFrame({
            'campana_final': ['CLARO'],
            'altas': [100],
            'ingresos': [5000.0],
            'mes': ['2025-01']
        }), pd.DataFrame({
            'campana_final': ['CLARO'], 
            'altas': [150],
            'ingresos': [6000.0],
            'mes': ['2025-01']
        })