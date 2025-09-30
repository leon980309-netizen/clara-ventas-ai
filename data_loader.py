import pandas as pd
from pathlib import Path
import unicodedata

def normalize_column_name(name):
    """
    Normaliza nombres de columnas: quita acentos, espacios, pone minúsculas y guiones bajos.
    Ej: "CAMPAÑA FINAL" → "campana_final"
    """
    if not isinstance(name, str):
        return name
    # Quitar acentos
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    # Reemplazar espacios por guiones bajos y poner en minúsculas
    return name.strip().lower().replace(' ', '_')

def cargar_datos(rutas):
    """
    Carga y combina datos de múltiples archivos Excel.
    Busca hojas 'Consolidado' y 'Metas Consolidado' (ignorando mayúsculas/espacios).
    """
    consolidados = []
    metas_list = []

    for ruta in rutas:
        ruta_path = Path(ruta)
        
        # Verificar que el archivo exista
        if not ruta_path.exists():
            print(f"⚠️ Archivo no encontrado: {ruta}")
            continue

        try:
            print(f"📂 Leyendo archivo: {ruta}")
            
            # Leer todas las hojas para diagnóstico
            excel_file = pd.ExcelFile(ruta)
            print(f"📄 Hojas disponibles: {excel_file.sheet_names}")

            # Buscar hoja 'Consolidado' (ignorando mayúsculas y espacios)
            hoja_consolidado = None
            for sheet in excel_file.sheet_names:
                if sheet.strip().lower() == "consolidado":
                    hoja_consolidado = sheet
                    break

            # Buscar hoja 'Metas Consolidado'
            hoja_metas = None
            for sheet in excel_file.sheet_names:
                if sheet.strip().lower() == "metas consolidado":
                    hoja_metas = sheet
                    break

            # Validar que las hojas necesarias existan
            if not hoja_consolidado:
                raise ValueError(f"❌ Hoja 'Consolidado' no encontrada en {ruta}. Hojas disponibles: {excel_file.sheet_names}")
            if not hoja_metas:
                raise ValueError(f"❌ Hoja 'Metas Consolidado' no encontrada en {ruta}. Hojas disponibles: {excel_file.sheet_names}")

            print(f"✅ Usando hoja 'Consolidado': '{hoja_consolidado}'")
            print(f"✅ Usando hoja 'Metas Consolidado': '{hoja_metas}'")

            # Leer las hojas
            df_consolidado = pd.read_excel(ruta, sheet_name=hoja_consolidado)
            df_metas = pd.read_excel(ruta, sheet_name=hoja_metas)

            # Mostrar columnas originales para diagnóstico
            print(f"📋 Columnas en '{hoja_consolidado}': {list(df_consolidado.columns)}")
            print(f"📋 Columnas en '{hoja_metas}': {list(df_metas.columns)}")

            # Normalizar nombres de columnas
            df_consolidado.columns = [normalize_column_name(c) for c in df_consolidado.columns]
            df_metas.columns = [normalize_column_name(c) for c in df_metas.columns]

            # Verificar que la columna clave exista
            if 'campana_final' not in df_consolidado.columns:
                raise KeyError(f"❌ Columna 'campana_final' no encontrada en '{hoja_consolidado}'. Columnas: {list(df_consolidado.columns)}")
            if 'campana_final' not in df_metas.columns:
                raise KeyError(f"❌ Columna 'campana_final' no encontrada en '{hoja_metas}'. Columnas: {list(df_metas.columns)}")

            # Limpiar y estandarizar valores en 'campana_final'
            df_consolidado['campana_final'] = df_consolidado['campana_final'].astype(str).str.strip().str.upper()
            df_metas['campana_final'] = df_metas['campana_final'].astype(str).str.strip().str.upper()

            consolidados.append(df_consolidado)
            metas_list.append(df_metas)
            print(f"✅ Archivo {ruta} cargado correctamente.")

        except Exception as e:
            print(f"❌ Error al procesar {ruta}: {e}")
            import traceback
            traceback.print_exc()

    # Combinar todos los DataFrames
    df_total = pd.concat(consolidados, ignore_index=True) if consolidados else pd.DataFrame()
    df_metas_total = pd.concat(metas_list, ignore_index=True) if metas_list else pd.DataFrame()

    return df_total, df_metas_total