import pandas as pd
from pathlib import Path
import unicodedata

def normalize_column_name(name):
    if not isinstance(name, str):
        return name
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return name.strip().lower().replace(' ', '_')

def cargar_datos(rutas):
    consolidados = []
    metas_list = []

    for ruta in rutas:
        if not Path(ruta).exists():
            print(f"⚠️ Archivo no encontrado: {ruta}")
            continue

        try:
            excel_file = pd.ExcelFile(ruta)
            print(f"\n📂 Archivo: {ruta}")
            print(f"📄 Hojas disponibles: {excel_file.sheet_names}")

            hoja_consolidado = None
            for sheet in excel_file.sheet_names:
                if sheet.strip().lower() == "consolidado":
                    hoja_consolidado = sheet
                    break

            hoja_metas = None
            for sheet in excel_file.sheet_names:
                if sheet.strip().lower() == "metas consolidado":
                    hoja_metas = sheet
                    break

            if not hoja_consolidado:
                raise ValueError(f"❌ No se encontró hoja 'Consolidado'. Hojas: {excel_file.sheet_names}")
            if not hoja_metas:
                raise ValueError(f"❌ No se encontró hoja 'Metas Consolidado'. Hojas: {excel_file.sheet_names}")

            print(f"✅ Usando hoja: '{hoja_consolidado}'")
            print(f"✅ Usando hoja: '{hoja_metas}'")

            df_consolidado = pd.read_excel(ruta, sheet_name=hoja_consolidado)
            df_metas = pd.read_excel(ruta, sheet_name=hoja_metas)

            print(f"📋 Columnas originales en '{hoja_consolidado}': {list(df_consolidado.columns)}")
            print(f"📋 Columnas originales en '{hoja_metas}': {list(df_metas.columns)}")

            df_consolidado.columns = [normalize_column_name(c) for c in df_consolidado.columns]
            df_metas.columns = [normalize_column_name(c) for c in df_metas.columns]

            print(f"✅ Columnas normalizadas en '{hoja_consolidado}': {list(df_consolidado.columns)}")
            print(f"✅ Columnas normalizadas en '{hoja_metas}': {list(df_metas.columns)}")

            if 'campana_final' not in df_consolidado.columns:
                raise KeyError(f"❌ 'campana_final' no encontrada. Columnas: {list(df_consolidado.columns)}")
            if 'campana_final' not in df_metas.columns:
                raise KeyError(f"❌ 'campana_final' no encontrada. Columnas: {list(df_metas.columns)}")

            df_consolidado['campana_final'] = df_consolidado['campana_final'].astype(str).str.strip().str.upper()
            df_metas['campana_final'] = df_metas['campana_final'].astype(str).str.strip().str.upper()

            consolidados.append(df_consolidado)
            metas_list.append(df_metas)

        except Exception as e:
            print(f"❌ Error al leer {ruta}: {e}")

    df_total = pd.concat(consolidados, ignore_index=True) if consolidados else pd.DataFrame()
    df_metas_total = pd.concat(metas_list, ignore_index=True) if metas_list else pd.DataFrame()

    return df_total, df_metas_total