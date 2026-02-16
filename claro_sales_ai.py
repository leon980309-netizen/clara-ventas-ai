import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import re
import json
import calendar
import time

# Festivos de Colombia 2024-2026
CO_HOLIDAYS = {
    "2024-01-01", "2024-01-08", "2024-03-25", "2024-03-28", "2024-03-29",
    "2024-05-01", "2024-05-13", "2024-06-03", "2024-06-10", "2024-07-01",
    "2024-07-20", "2024-08-07", "2024-08-19", "2024-10-14", "2024-11-04",
    "2024-11-11", "2024-12-08", "2024-12-25",
    "2025-01-01", "2025-01-06", "2025-03-24", "2025-04-17", "2025-04-18",
    "2025-05-01", "2025-06-02", "2025-06-30", "2025-07-20", "2025-08-07",
    "2025-08-18", "2025-10-13", "2025-11-03", "2025-11-17", "2025-12-08", "2025-12-25",
    "2026-01-01", "2026-01-06", "2026-03-23", "2026-04-02", "2026-04-03",
    "2026-05-01", "2026-06-01", "2026-06-29", "2026-07-20", "2026-08-07",
    "2026-08-17", "2026-10-12", "2026-11-02", "2026-11-16", "2026-12-08", "2026-12-25"
}

class ClaraIA:
    def __init__(self, url_consolidado, url_metas):
        self.homologacion_aliados = {
            'ABAI Masivo': 'ABAI', 'ABAI Proactivo': 'ABAI', 'ABAI Segundo Anillo': 'ABAI',
            'ABAI Tercer Anillo': 'ABAI', 'ABAI Whatsapp': 'ABAI',
            'Almacontact Swat': 'ALMACONTACT',
            'AQI Segundo Anillo': 'AQI', 'AQI Masivo Barranquilla': 'AQI',
            'AQI Tercer Anillo': 'AQI', 'AQI Whatsapp': 'AQI',
            'Atento Segundo Anillo': 'ATENTO', 'Atento Clientes Criticos': 'ATENTO',
            'Atento Proactivo': 'ATENTO', 'Atento Swat Bogotá': 'ATENTO',
            'Atento Traslados Pereira': 'ATENTO',
            'BRM Filtro': 'BRM', 'BRM Masivo Medellín': 'BRM',
            'BRM Tercer Anillo': 'BRM', 'BRM Whatsapp': 'BRM',
            'COS Fidelización Bogotá': 'COS', 'COS Masivo Bogotá': 'COS',
            'COS Recuperación Bogotá': 'COS', 'COS Segundo Anillo': 'COS',
            'COS Upselling': 'COS', 'COS Whatsapp': 'COS',
            'IBR Latam SAC': 'IBR', 'Latcom': 'LATCOM',
            'Millenium Masivo': 'MILLENIUM', 'Millenium Web Center': 'MILLENIUM',
            'Nexa Masivo': 'NEXA'
        }
        
        self.especialistas = {
            'Cristian Villamil': ['COS', 'BRM'],
            'Annie Solano': ['AQI', 'MILLENIUM', 'ALMACONTACT', 'LATCOM'],
            'Geovanny Ramirez': ['NEXA', 'ABAI', 'ATENTO']
        }
        
        self.intents = {
            'variacion': [r'variacion', r'variación', r'cambio', r'diferencia', r'comparar.*vs', r'vs.*', r'crecimiento', r'caida', r'caída'],
            'cumplimiento': [r'cumplimiento', r'meta', r'objetivo', r'porcentaje', r'cuanto falta', r'progreso'],
            'ranking': [r'ranking', r'top', r'mejores', r'mayores', r'quien vendio', r'quién vendió', r'lider', r'campeon', r'posicion', r'posición'],
            'comportamiento': [r'comportamiento', r'total', r'global', r'general', r'ultimos 3 meses', r'últimos 3 meses', r'tendencia', r'grafica', r'gráfico', r'chart'],
            'producto_estrella': [r'producto mas vendido', r'producto más vendido', r'estrella', r'producto fuerte', r'producto principal', r'mas vendido', r'más vendido'],
            'desempeno_especialista': [r'geovanny', r'geovany', r'cristian', r'annie', r'equipo de', r'aliados de'],
            'desempeno_aliado': [r'desempeno', r'desempeño', r'como le fue', r'como va', r'como esta', r'como vamos', r'como estan', r'rendimiento', r'ventas de', r'cuanto vendio', r'cuánto vendió'],
            'brecha': [r'brecha', r'gap', r'diferencia meta', r'falta para meta', r'cuanto falta', r'desviacion', r'desviación']
        }
        
        self.sales_df = self.load_csv_from_url(url_consolidado)
        self.metas_df = self.load_csv_from_url(url_metas)
        
        self._indexar_datos_dinamicos()
        
        print(f"✅ Datos cargados: {len(self.sales_df)} filas de ventas, {len(self.metas_df)} filas de metas")
        print(f"🔍 Aliados únicos encontrados: {len(self.aliados_unicos)}")
        print(f"🔍 Campañas únicas encontradas: {len(self.campanas_unicas)}")
        print(f"🔍 Productos únicos encontrados: {len(self.productos_unicos)}")

    def _indexar_datos_dinamicos(self):
        self.aliados_unicos = set()
        self.campanas_unicas = set()
        self.productos_unicos = set()
        
        if not self.sales_df.empty:
            if 'ALIADO' in self.sales_df.columns:
                self.aliados_unicos = set(self.sales_df['ALIADO'].dropna().unique())
            if 'CAMPAÑA FINAL' in self.sales_df.columns:
                self.campanas_unicas = set(self.sales_df['CAMPAÑA FINAL'].dropna().unique())
            if 'BASE' in self.sales_df.columns:
                self.productos_unicos = set(self.sales_df['BASE'].dropna().unique())
            
            self.aliados_unicos.update(self.homologacion_aliados.values())

    def load_csv_from_url(self, url):
        try:
            response = requests.get(url.strip(), timeout=30)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text), sep=';', low_memory=False)
            
            if 'MES' in df.columns:
                df['MES'] = pd.to_datetime(df['MES'], format='%d/%m/%Y', errors='coerce')
                df = df.dropna(subset=['MES'])
                df['Mes_Año'] = df['MES'].dt.strftime('%Y-%m')
                df['Dia'] = df['MES'].dt.day
                df['Fecha_Str'] = df['MES'].dt.strftime('%Y-%m-%d')
            
            if 'ALTAS' in df.columns:
                df['ALTAS'] = pd.to_numeric(df['ALTAS'], errors='coerce').fillna(0)
            
            if 'INGRESOS' in df.columns:
                df['INGRESOS'] = pd.to_numeric(
                    df['INGRESOS'].astype(str).str.replace(r'[$\s.]', '', regex=True).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0)
            
            if 'CAMPAÑA FINAL' in df.columns and 'ALIADO' not in df.columns:
                df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna(df['CAMPAÑA FINAL'])
            
            return df
        except Exception as e:
            print(f"❌ Error cargando datos: {e}")
            return pd.DataFrame()

    def get_current_month(self):
        if not self.sales_df.empty and 'Mes_Año' in self.sales_df.columns:
            return self.sales_df['Mes_Año'].max()
        return datetime.now().strftime('%Y-%m')

    def get_last_n_months(self, n=3):
        if self.sales_df.empty or 'Mes_Año' not in self.sales_df.columns:
            return []
        return sorted(self.sales_df['Mes_Año'].unique(), reverse=True)[:n]

    def _extract_aliado(self, text):
        text_lower = text.lower()
        for aliado in self.homologacion_aliados.values():
            if aliado.lower() in text_lower:
                return aliado
        for campana, aliado in self.homologacion_aliados.items():
            if campana.lower() in text_lower:
                return aliado
        for aliado in self.aliados_unicos:
            if isinstance(aliado, str) and len(aliado) > 2:
                aliado_lower = aliado.lower()
                if aliado_lower in text_lower or (len(aliado) >= 4 and aliado_lower[:4] in text_lower):
                    return aliado
        for aliado in self.aliados_unicos:
            if isinstance(aliado, str) and len(aliado) >= 4:
                palabras_aliado = aliado.lower().split()
                for palabra in palabras_aliado:
                    if len(palabra) >= 4 and palabra in text_lower:
                        return aliado
        return None

    def _extract_campana(self, text):
        text_lower = text.lower()
        for campana in self.campanas_unicas:
            if isinstance(campana, str) and len(campana) > 3:
                campana_lower = campana.lower()
                if campana_lower in text_lower or text_lower in campana_lower:
                    return campana
        for campana in self.campanas_unicas:
            if isinstance(campana, str):
                palabras_campana = campana.lower().split()
                for palabra in palabras_campana:
                    if len(palabra) >= 4 and palabra in text_lower:
                        return campana
        return None

    def _extract_producto(self, text):
        text_lower = text.lower()
        mapping = {
            "fijo": "fijo", "fibra": "fijo", "telefono fijo": "fijo", "línea fija": "fijo", "linea fija": "fijo",
            "movil": "m", "móvil": "m", "celular": "m", "linea movil": "m", "línea movil": "m", "smartphone": "m",
            "adicional": "adicional", "extra": "adicional", "plus": "adicional", "complementario": "adicional"
        }
        for keyword, producto in mapping.items():
            if keyword in text_lower:
                return producto
        for prod in self.productos_unicos:
            if isinstance(prod, str) and len(prod) > 2:
                prod_lower = prod.lower()
                if prod_lower in text_lower or text_lower in prod_lower:
                    return prod
        for prod in self.productos_unicos:
            if isinstance(prod, str):
                palabras_prod = prod.lower().split()
                for palabra in palabras_prod:
                    if len(palabra) >= 3 and palabra in text_lower:
                        return prod
        return None

    def _extract_mes(self, text):
        text_lower = text.lower()
        meses_map = {
            'enero':'01','ene':'01','feb':'02','febrero':'02','marzo':'03','mar':'03',
            'abr':'04','abril':'04','mayo':'05','may':'05','jun':'06','junio':'06',
            'jul':'07','julio':'07','ago':'08','agosto':'08','sep':'09','septiembre':'09',
            'oct':'10','octubre':'10','nov':'11','noviembre':'11','dic':'12','diciembre':'12'
        }
        pattern = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\s*(\d{4})"
        match = re.search(pattern, text_lower)
        if match:
            return f"{match.group(2)}-{meses_map.get(match.group(1), '01')}"
        if "mes pasado" in text_lower or "mes anterior" in text_lower:
            hoy = datetime.now()
            if hoy.month == 1:
                return f"{hoy.year - 1}-12"
            else:
                return f"{hoy.year}-{(hoy.month - 1):02d}"
        if "este mes" in text_lower or "mes actual" in text_lower or "mes en curso" in text_lower:
            hoy = datetime.now()
            return f"{hoy.year}-{hoy.month:02d}"
        return None

    def _extract_dos_meses(self, text):
        meses_map = {
            'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06',
            'julio':'07','agosto':'08','septiembre':'09','octubre':'10','noviembre':'11','diciembre':'12'
        }
        pattern = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(\d{4})"
        matches = re.findall(pattern, text.lower())
        if len(matches) >= 2:
            m1, a1 = matches[0]
            m2, a2 = matches[1]
            return f"{a1}-{meses_map.get(m1, '01')}", f"{a2}-{meses_map.get(m2, '01')}"
        return None, None

    def _extract_fecha_especifica(self, text):
        text_lower = text.lower()
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        pattern = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})'
        match = re.search(pattern, text_lower)
        if match:
            dia = int(match.group(1))
            mes = meses_map[match.group(2)]
            anio = int(match.group(3))
            return datetime(anio, mes, dia)
        return None

    def _detect_intent(self, text):
        text_lower = text.lower()
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        return None

    # === MÉTODOS ANALÍTICOS ===
    def get_desempeno_por_especialista(self, nombre_especialista, mes=None):
        if mes is None: mes = self.get_current_month()
        if nombre_especialista not in self.especialistas: return None
        aliados = self.especialistas[nombre_especialista]
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['ALIADO'].isin(aliados)]
        return df_f.groupby('ALIADO').agg({'ALTAS': 'sum', 'INGRESOS': 'sum'}).reset_index().to_dict(orient='records')

    def get_variacion_mes_a_mes(self, aliado, producto, mes1, mes2):
        df = self.sales_df.copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[(df['ALIADO'] == aliado)]
        if producto:
            df_f = df_f[df_f['BASE'].str.contains(producto, case=False, na=False)]
        ventas1 = df_f[df_f['Mes_Año'] == mes1]['ALTAS'].sum()
        ventas2 = df_f[df_f['Mes_Año'] == mes2]['ALTAS'].sum()
        variacion = float('inf') if ventas2 == 0 and ventas1 > 0 else ((ventas1 - ventas2) / ventas2) * 100 if ventas2 != 0 else 0
        return {'mes1': mes1, 'mes2': mes2, 'ventas1': int(ventas1), 'ventas2': int(ventas2), 'variacion_pct': round(variacion, 2)}

    def get_ranking_vendedores_por_producto(self, producto=None, mes=None, campana=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if producto:
            df = df[df['BASE'].str.contains(producto, case=False, na=False)]
        if campana:
            df = df[df['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False)]
        return df.groupby(['ALIADO', 'CAMPAÑA FINAL']).agg({'ALTAS': 'sum', 'INGRESOS': 'sum'}).reset_index().sort_values('ALTAS', ascending=False).to_dict(orient='records')

    def get_comportamiento_total_operacion(self):
        meses = self.get_last_n_months(3)
        df = self.sales_df[self.sales_df['Mes_Año'].isin(meses)].copy()
        return df.groupby('Mes_Año').agg({'ALTAS': 'sum', 'INGRESOS': 'sum'}).reindex(meses, fill_value=0).reset_index().to_dict(orient='records')

    def get_producto_mas_vendido_por_aliado(self, aliado, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['ALIADO'] == aliado]
        if df_f.empty: return None
        top = df_f.groupby('BASE')['ALTAS'].sum().sort_values(ascending=False).head(1)
        return {'aliado': aliado, 'producto': top.index[0], 'altas': int(top.iloc[0]), 'mes': mes}

    def get_cumplimiento_detalle(self, aliado=None, producto=None, mes=None, campana=None):
        if mes is None: mes = self.get_current_month()
        ventas = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        ventas['ALIADO'] = ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: ventas = ventas[ventas['ALIADO'] == aliado]
        if producto: ventas = ventas[ventas['BASE'].str.contains(producto, case=False, na=False, regex=False)]
        if campana: ventas = ventas[ventas['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False)]
        ventas_reales = ventas.groupby('BASE').agg({'ALTAS':'sum','INGRESOS':'sum'}).reset_index()
        ventas_reales.columns = ['BASE', 'ALTAS_REALES', 'INGRESOS_REALES']

        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: metas = metas[metas['ALIADO'] == aliado]
        if producto: metas = metas[metas['BASE'].str.contains(producto, case=False, na=False, regex=False)]
        if campana: metas = metas[metas['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False)]
        metas['Ingresos'] = pd.to_numeric(metas['Ingresos'].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0'), errors='coerce').fillna(0)
        metas_reales = metas.groupby('BASE').agg({'Altas':'sum','Ingresos':'sum'}).reset_index()
        metas_reales.columns = ['BASE', 'META_ALTAS', 'META_INGRESOS']

        cumplimiento = pd.merge(ventas_reales, metas_reales, on='BASE', how='outer').fillna(0)
        cumplimiento['CUMPLIMIENTO_ALTAS_%'] = round((cumplimiento['ALTAS_REALES'] / cumplimiento['META_ALTAS'].replace(0,1)) * 100, 2)
        cumplimiento['CUMPLIMIENTO_INGRESOS_%'] = round((cumplimiento['INGRESOS_REALES'] / cumplimiento['META_INGRESOS'].replace(0,1)) * 100, 2)
        return cumplimiento.replace([float('inf'), -float('inf')], 0).to_dict(orient='records')

    def get_desempeno_aliado(self, aliado, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df = df[df['ALIADO'] == aliado]
        if df.empty: return None
        return {'aliado': aliado, 'mes': mes, 'altas': int(df['ALTAS'].sum()), 'ingresos': float(df['INGRESOS'].sum())}

    def _calcular_brecha_por_fecha(self, aliado=None, producto=None, campana=None, fecha_limite=None, tipo='altas'):
        if fecha_limite is None:
            mes = self.get_current_month()
            fecha_inicio = datetime.strptime(f"{mes}-01", "%Y-%m-%d")
            dias_mes = calendar.monthrange(fecha_inicio.year, fecha_inicio.month)[1]
            fecha_fin = fecha_inicio.replace(day=dias_mes)
        else:
            fecha_inicio = fecha_limite.replace(day=1)
            fecha_fin = fecha_limite
        
        df_ventas = self.sales_df.copy()
        df_ventas['ALIADO'] = df_ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: df_ventas = df_ventas[df_ventas['ALIADO'] == aliado]
        if producto: df_ventas = df_ventas[df_ventas['BASE'].str.contains(producto, case=False, na=False)]
        if campana: df_ventas = df_ventas[df_ventas['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False)]
        df_ventas = df_ventas[(df_ventas['MES'] >= fecha_inicio) & (df_ventas['MES'] <= fecha_fin)]
        ejecutado = df_ventas['ALTAS'].sum() if tipo == 'altas' else df_ventas['INGRESOS'].sum()
        
        df_metas = self.metas_df.copy()
        df_metas['MES'] = pd.to_datetime(df_metas['MES'], format='%d/%m/%Y', errors='coerce')
        df_metas = df_metas.dropna(subset=['MES'])
        df_metas['ALIADO'] = df_metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: df_metas = df_metas[df_metas['ALIADO'] == aliado]
        if producto: df_metas = df_metas[df_metas['BASE'].str.contains(producto, case=False, na=False, regex=False)]
        if campana: df_metas = df_metas[df_metas['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False)]
        df_metas = df_metas[(df_metas['MES'] >= fecha_inicio) & (df_metas['MES'] <= fecha_fin)]
        col_meta = 'Altas' if tipo == 'altas' else 'Ingresos'
        df_metas[col_meta] = pd.to_numeric(df_metas[col_meta].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0'), errors='coerce').fillna(0)
        meta = df_metas[col_meta].sum()
        
        brecha = ejecutado - meta
        cumplimiento_pct = round((ejecutado / meta * 100) if meta > 0 else 0, 2)
        
        return {
            'ejecutado': round(ejecutado, 2),
            'meta': round(meta, 2),
            'brecha': round(brecha, 2),
            'cumplimiento_pct': cumplimiento_pct,
            'fecha_inicio': fecha_inicio.strftime('%d/%m/%Y'),
            'fecha_fin': fecha_fin.strftime('%d/%m/%Y')
        }

    def _calcular_brecha_detalle_campanas(self, aliado, producto=None, fecha_limite=None):
        if fecha_limite is None:
            mes = self.get_current_month()
            fecha_inicio = datetime.strptime(f"{mes}-01", "%Y-%m-%d")
            dias_mes = calendar.monthrange(fecha_inicio.year, fecha_inicio.month)[1]
            fecha_fin = fecha_inicio.replace(day=dias_mes)
        else:
            fecha_inicio = fecha_limite.replace(day=1)
            fecha_fin = fecha_limite
        
        resultados = []
        df_ventas = self.sales_df[self.sales_df['Mes_Año'] == fecha_inicio.strftime('%Y-%m')].copy()
        df_ventas['ALIADO'] = df_ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_ventas = df_ventas[df_ventas['ALIADO'] == aliado]
        if producto:
            df_ventas = df_ventas[df_ventas['BASE'].str.contains(producto, case=False, na=False)]
        
        campanas = df_ventas['CAMPAÑA FINAL'].unique()
        total_ejecutado = 0
        total_meta = 0
        
        for campana in campanas:
            ejecutado = df_ventas[df_ventas['CAMPAÑA FINAL'] == campana]['ALTAS'].sum()
            total_ejecutado += ejecutado
            
            df_metas = self.metas_df.copy()
            df_metas['MES'] = pd.to_datetime(df_metas['MES'], format='%d/%m/%Y', errors='coerce')
            df_metas = df_metas.dropna(subset=['MES'])
            df_metas = df_metas[(df_metas['MES'] >= fecha_inicio) & (df_metas['MES'] <= fecha_fin)]
            df_metas['ALIADO'] = df_metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
            df_metas = df_metas[(df_metas['ALIADO'] == aliado) & (df_metas['CAMPAÑA FINAL'].str.contains(campana, case=False, na=False))]
            if producto:
                df_metas = df_metas[df_metas['BASE'].str.contains(producto, case=False, na=False, regex=False)]
            df_metas['Altas'] = pd.to_numeric(df_metas['Altas'].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0'), errors='coerce').fillna(0)
            meta = df_metas['Altas'].sum()
            total_meta += meta
            
            brecha = ejecutado - meta
            resultados.append({
                'campana': campana,
                'ejecutado': int(ejecutado),
                'meta': int(meta),
                'brecha': int(brecha),
                'cumplimiento_pct': round((ejecutado / meta * 100) if meta > 0 else 0, 2)
            })
        
        brecha_total = total_ejecutado - total_meta
        resultados.append({
            'campana': '📊 TOTAL',
            'ejecutado': int(total_ejecutado),
            'meta': int(total_meta),
            'brecha': int(brecha_total),
            'cumplimiento_pct': round((total_ejecutado / total_meta * 100) if total_meta > 0 else 0, 2),
            'es_total': True
        })
        
        return resultados

    # === 🔥 GENERACIÓN DE GRÁFICAS CON JSON CONFIG (SOLUCIÓN DEFINITIVA) ===

    def _generar_grafica_comportamiento(self, datos, titulo="Comportamiento"):
        labels = [d['Mes_Año'] for d in datos]
        altas = [int(d['ALTAS']) for d in datos]
        ingresos = [float(d['INGRESOS']) for d in datos]
        chart_id = f"chartComportamiento_{int(time.time() * 1000)}"
        
        chart_config = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Altas",
                        "data": altas,
                        "borderColor": "#b61a23",
                        "backgroundColor": "rgba(182, 26, 35, 0.1)",
                        "tension": 0.4,
                        "fill": True
                    },
                    {
                        "label": "Ingresos ($)",
                        "data": ingresos,
                        "borderColor": "#0097a9",
                        "backgroundColor": "rgba(0, 151, 169, 0.1)",
                        "tension": 0.4,
                        "fill": True,
                        "yAxisID": "y1"
                    }
                ]
            },
            "options": {
                "responsive": True,
                "interaction": {"mode": "index", "intersect": False},
                "scales": {
                    "y": {"type": "linear", "display": True, "position": "left", "title": {"display": True, "text": "Altas"}},
                    "y1": {"type": "linear", "display": True, "position": "right", "grid": {"drawOnChartArea": False}, "title": {"display": True, "text": "Ingresos"}}
                },
                "plugins": {
                    "title": {"display": True, "text": titulo, "font": {"size": 16}},
                    "legend": {"position": "bottom"}
                }
            }
        }
        
        return f'''
        <div style="margin: 15px 0; background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <canvas id="{chart_id}" height="250"></canvas>
            <script type="chart-config">
            {{"chartId": "{chart_id}", "config": {json.dumps(chart_config)}}}
            </script>
        </div>
        '''

    def _generar_grafica_cumplimiento(self, cumplimiento_data, aliado, mes):
        productos = [str(d['BASE']) for d in cumplimiento_data[:10]]
        cumplimiento_altas = [float(d['CUMPLIMIENTO_ALTAS_%']) for d in cumplimiento_data[:10]]
        cumplimiento_ingresos = [float(d['CUMPLIMIENTO_INGRESOS_%']) for d in cumplimiento_data[:10]]
        colors_altas = ['#28a745' if v >= 100 else '#b61a23' for v in cumplimiento_altas]
        colors_ingresos = ['#28a745' if v >= 100 else '#0097a9' for v in cumplimiento_ingresos]
        chart_id = f"chartCumplimiento_{int(time.time() * 1000)}"
        
        chart_config = {
            "type": "bar",
            "data": {
                "labels": productos,
                "datasets": [
                    {
                        "label": "Cumplimiento Altas (%)",
                        "data": cumplimiento_altas,
                        "backgroundColor": colors_altas,
                        "borderWidth": 1
                    },
                    {
                        "label": "Cumplimiento Ingresos (%)",
                        "data": cumplimiento_ingresos,
                        "backgroundColor": colors_ingresos,
                        "borderWidth": 1
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {"y": {"beginAtZero": True, "max": 150, "title": {"display": True, "text": "Cumplimiento (%)"}}},
                "plugins": {
                    "title": {"display": True, "text": f"Cumplimiento de Metas - {aliado} ({mes})", "font": {"size": 16}},
                    "legend": {"position": "bottom"}
                }
            }
        }
        
        return f'''
        <div style="margin: 15px 0; background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <canvas id="{chart_id}" height="300"></canvas>
            <script type="chart-config">
            {{"chartId": "{chart_id}", "config": {json.dumps(chart_config)}}}
            </script>
        </div>
        '''

    def _generar_grafica_brechas(self, datos_brecha, titulo="Análisis de Brechas"):
        if not datos_brecha or 'campanas' not in datos_brecha:
            return ""
        campanas = [str(d['campana']) for d in datos_brecha['campanas']]
        brechas = [int(d['brecha']) for d in datos_brecha['campanas']]
        colors = ['#28a745' if b >= 0 else '#b61a23' for b in brechas]
        chart_id = f"chartBrechas_{int(time.time() * 1000)}"
        
        chart_config = {
            "type": "bar",
            "data": {
                "labels": campanas,
                "datasets": [{
                    "label": "Brecha (Ejecutado - Meta)",
                    "data": brechas,
                    "backgroundColor": colors,
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "indexAxis": "y",
                "scales": {
                    "x": {"title": {"display": True, "text": "Brecha"}, "grid": {"color": "#eee"}},
                    "y": {"ticks": {"autoSkip": False}, "grid": {"display": False}}
                },
                "plugins": {
                    "title": {"display": True, "text": titulo, "font": {"size": 16}},
                    "legend": {"display": False}
                }
            }
        }
        
        return f'''
        <div style="margin: 15px 0; background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <canvas id="{chart_id}" height="300"></canvas>
            <script type="chart-config">
            {{"chartId": "{chart_id}", "config": {json.dumps(chart_config)}}}
            </script>
        </div>
        '''

    def _generate_html_table(self, headers, rows):
        html = '<table style="width:100%; border-collapse: collapse; margin: 10px 0; font-size: 14px;">'
        html += '<thead><tr style="background-color:#b61a23; color:white;">'
        for h in headers: html += f'<th style="padding:10px; text-align:left;">{h}</th>'
        html += '</tr></thead><tbody>'
        for i, row in enumerate(rows):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            html += f'<tr style="background-color:{bg}; border-bottom:1px solid #eee;">'
            for cell in row: html += f'<td style="padding:10px;">{cell}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        return html

    def _help_message(self):
        return '''
        <div style="background:#f5f5f5; padding:15px; border-radius:10px; margin:10px 0;">
            <p style="margin:0 0 10px 0;"><strong>🤖 Pregúntame de forma natural sobre CUALQUIER dato:</strong></p>
            <ul style="padding-left:20px; margin:0; color:#555; font-size:14px; line-height:1.8;">
                <li><strong>📈 Gráficas:</strong> "Comportamiento total con gráfica", "Cumplimiento de COS con chart"</li>
                <li><strong>🎯 Cumplimiento:</strong> "Cumplimiento de [CUALQUIER ALIADO] este mes"</li>
                <li><strong>📊 Brechas:</strong> "Brecha de [CUALQUIER ALIADO]", "Brecha a 15 de febrero de 2026"</li>
                <li><strong>🏆 Ranking:</strong> "Ranking de vendedores para [CUALQUIER PRODUCTO]"</li>
                <li><strong>🔍 Detalle:</strong> "Brecha de [ALIADO] para [PRODUCTO]" (muestra campañas con sus brechas)</li>
                <li><strong>📅 Fechas:</strong> "Variación entre agosto 2024 y septiembre 2024", "Cumplimiento mes pasado"</li>
            </ul>
            <p style="margin:10px 0 0 0; font-size:13px; color:#888;">
                💡 <strong>Tip:</strong> Funciona con CUALQUIER aliado, campaña, producto o fecha que exista en tus datos.
            </p>
        </div>
        '''

    # === HANDLERS DE RESPUESTA ===
    def _handle_variacion_custom(self, aliado, producto, mes1, mes2):
        res = self.get_variacion_mes_a_mes(aliado, producto, mes1, mes2)
        if res['ventas1'] == 0 and res['ventas2'] == 0:
            return f"<p>❌ No hay datos de ventas para '{producto}' en {aliado} en esos meses.</p>"
        color = "#28a745" if res['variacion_pct'] > 0 else "#b61a23"
        tendencia = "crecimiento 📈" if res['variacion_pct'] > 0 else "caída 📉" if res['variacion_pct'] < 0 else "estable ➡️"
        return f'''
        <div style="background:#fff; padding:20px; border-left: 5px solid {color}; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-radius:8px;">
            <h3 style="color:#b61a23; margin-top:0;">📊 Variación {producto.upper() if producto else 'GENERAL'} - {aliado}</h3>
            <div style="display:flex; justify-content:space-around; margin: 20px 0;">
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px; flex:1; margin:0 5px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">{res['mes1']}</div>
                    <div style="font-size:24px; font-weight:bold; color:#333;">{res['ventas1']:,}</div>
                </div>
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px; flex:1; margin:0 5px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">{res['mes2']}</div>
                    <div style="font-size:24px; font-weight:bold; color:#333;">{res['ventas2']:,}</div>
                </div>
            </div>
            <div style="text-align:center; padding:15px; background:{color}15; border-radius:10px; margin:15px 0;">
                <div style="font-size:14px; color:#666;">Variación</div>
                <div style="font-size:28px; font-weight:bold; color:{color};">{res['variacion_pct']:+.2f}%</div>
            </div>
            <p><strong>🔍 Análisis:</strong> La variación de <strong style='color:{color};'>{res['variacion_pct']:+.2f}%</strong> indica {tendencia}.</p>
        </div>
        '''

    def _handle_cumplimiento_custom(self, aliado, mes):
        cumplimiento = self.get_cumplimiento_detalle(aliado=aliado, mes=mes)
        if not cumplimiento: return f"<p>❌ No hay datos de cumplimiento para {aliado} en {mes}.</p>"
        item = cumplimiento[0]
        color_altas = "#28a745" if item['CUMPLIMIENTO_ALTAS_%'] >= 100 else "#b61a23"
        color_ingresos = "#28a745" if item['CUMPLIMIENTO_INGRESOS_%'] >= 100 else "#0097a9"
        return f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3 style="color:#b61a23; margin-top:0;">🎯 Cumplimiento: {aliado}</h3>
            <p style="color:#666; font-size:14px; margin:5px 0 15px 0;">Mes: <strong>{mes}</strong></p>
            <div style="margin: 20px 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="font-weight:600;">📈 Altas:</span>
                    <strong>{int(item['ALTAS_REALES']):,} / {int(item['META_ALTAS']):,}</strong>
                </div>
                <div style="width:100%; background:#e0e0e0; height:12px; border-radius:6px; overflow:hidden;">
                    <div style="width:{min(item['CUMPLIMIENTO_ALTAS_%'], 100)}%; background:{color_altas}; height:100%;"></div>
                </div>
                <div style="text-align:right; font-size:14px; font-weight:bold; color:{color_altas}; margin-top:5px;">{item['CUMPLIMIENTO_ALTAS_%']}%</div>
            </div>
            <div style="margin: 20px 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="font-weight:600;">💰 Ingresos:</span>
                    <strong>${float(item['INGRESOS_REALES']):,.0f} / ${float(item['META_INGRESOS']):,.0f}</strong>
                </div>
                <div style="width:100%; background:#e0e0e0; height:12px; border-radius:6px; overflow:hidden;">
                    <div style="width:{min(item['CUMPLIMIENTO_INGRESOS_%'], 100)}%; background:{color_ingresos}; height:100%;"></div>
                </div>
                <div style="text-align:right; font-size:14px; font-weight:bold; color:{color_ingresos}; margin-top:5px;">{item['CUMPLIMIENTO_INGRESOS_%']}%</div>
            </div>
        </div>
        '''

    def _handle_cumplimiento_con_grafica(self, aliado, mes):
        cumplimiento = self.get_cumplimiento_detalle(aliado=aliado, mes=mes)
        if not cumplimiento: return f"<p>❌ No hay datos de cumplimiento para {aliado} en {mes}.</p>"
        grafica = self._generar_grafica_cumplimiento(cumplimiento, aliado, mes)
        item = cumplimiento[0]
        color_altas = "#28a745" if item['CUMPLIMIENTO_ALTAS_%'] >= 100 else "#b61a23"
        color_ingresos = "#28a745" if item['CUMPLIMIENTO_INGRESOS_%'] >= 100 else "#0097a9"
        return f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3 style="color:#b61a23; margin:0 0 10px 0;">🎯 Cumplimiento: {aliado}</h3>
            <p style="color:#666; font-size:14px; margin:0 0 20px 0;">Mes: <strong>{mes}</strong></p>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:20px;">
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">Cumplimiento Altas</div>
                    <div style="font-size:28px; font-weight:bold; color:{color_altas}; margin:10px 0;">{item['CUMPLIMIENTO_ALTAS_%']}%</div>
                </div>
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">Cumplimiento Ingresos</div>
                    <div style="font-size:28px; font-weight:bold; color:{color_ingresos}; margin:10px 0;">{item['CUMPLIMIENTO_INGRESOS_%']}%</div>
                </div>
            </div>
            {grafica}
        </div>
        '''

    def _handle_comportamiento_con_grafica(self):
        datos = self.get_comportamiento_total_operacion()
        if not datos: return "<p>❌ No hay datos para los últimos 3 meses.</p>"
        total_altas = sum(d['ALTAS'] for d in datos)
        total_ingresos = sum(d['INGRESOS'] for d in datos)
        grafica = self._generar_grafica_comportamiento(datos, "📈 Tendencia Operación - Últimos 3 Meses")
        return f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3 style="color:#b61a23; margin:0 0 15px 0;">📊 Comportamiento Total</h3>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:20px;">
                <div style="background:linear-gradient(135deg, #b61a23, #901219); color:white; padding:20px; border-radius:10px; text-align:center;">
                    <div style="font-size:14px; opacity:0.9;">Total Altas</div>
                    <div style="font-size:32px; font-weight:bold; margin:10px 0;">{total_altas:,}</div>
                </div>
                <div style="background:linear-gradient(135deg, #0097a9, #007d8c); color:white; padding:20px; border-radius:10px; text-align:center;">
                    <div style="font-size:14px; opacity:0.9;">Total Ingresos</div>
                    <div style="font-size:32px; font-weight:bold; margin:10px 0;">${total_ingresos:,.0f}</div>
                </div>
            </div>
            {grafica}
        </div>
        '''

    def _handle_ranking_custom(self, producto, mes, campana=None):
        ranking = self.get_ranking_vendedores_por_producto(producto=producto, mes=mes, campana=campana)
        if not ranking: return "<p>❌ No hay datos para el ranking.</p>"
        prod_text = f" para {producto}" if producto else ""
        camp_text = f" en {campana}" if campana else ""
        html = f"<h3 style='color:#b61a23; margin:0 0 15px 0;'>🏆 Ranking{prod_text}{camp_text} en {mes}</h3><table style='width:100%; border-collapse:collapse; background:#fff; border-radius:10px; overflow:hidden; box-shadow:0 2px 10px rgba(0,0,0,0.05);'>"
        for i, row in enumerate(ranking[:10]):
            bg = "#fff5f5" if i == 0 else "#f9f9f9" if i < 3 else "#fff"
            icono = ["🥇 1º","🥈 2º","🥉 3º"][i] if i < 3 else f"{i+1}º"
            html += f"<tr style='background:{bg}; border-bottom:1px solid #eee;'><td style='padding:12px 15px; font-weight:bold; color:#b61a23;'>{icono}</td><td style='padding:12px 15px; font-weight:600;'>{row['CAMPAÑA FINAL']}</td><td style='padding:12px 15px; text-align:right; font-weight:bold; color:#b61a23;'>{int(row['ALTAS']):,}</td></tr>"
        html += "</table>"
        return html

    def _handle_producto_mas_vendido_custom(self, aliado, mes):
        res = self.get_producto_mas_vendido_por_aliado(aliado, mes)
        if not res: return f"<p>❌ Sin datos para {aliado}.</p>"
        return f'''
        <div style="text-align:center; padding:25px; background: linear-gradient(135deg, #0097a9, #007d8c); color:white; border-radius:15px;">
            <div style="font-size:50px;">🔥</div>
            <h3 style="margin:10px 0;">Producto Estrella</h3>
            <p style="font-size:14px; opacity:0.8;">Para {aliado} en {mes}</p>
            <div style="font-size:28px; font-weight:bold; margin:20px 0; background:rgba(255,255,255,0.2); padding:15px; border-radius:10px;">{res['producto'].upper()}</div>
            <div style="display:inline-block; background:rgba(255,255,255,0.2); padding:10px 25px; border-radius:25px;">{res['altas']:,} Altas</div>
        </div>
        '''

    def _handle_brecha_producto_aliado(self, aliado, producto=None, fecha_text=None, campana=None):
        fecha_limite = self._extract_fecha_especifica(fecha_text) if fecha_text else None
        mes_ref = fecha_limite.strftime('%Y-%m') if fecha_limite else self.get_current_month()
        fecha_display = fecha_limite.strftime('%d/%m/%Y') if fecha_limite else "Mes completo"
        
        brecha_total = self._calcular_brecha_por_fecha(aliado=aliado, producto=producto, campana=campana, fecha_limite=fecha_limite)
        detalle_campanas = self._calcular_brecha_detalle_campanas(aliado, producto=producto, fecha_limite=fecha_limite)
        grafica = self._generar_grafica_brechas({'campanas': detalle_campanas}, f"Brechas por Campaña - {aliado}")
        
        tabla_rows = ""
        for item in detalle_campanas:
            color_brecha = "#28a745" if item['brecha'] >= 0 else "#b61a23"
            icono = "✅" if item['brecha'] >= 0 else "❌"
            estilo = "font-weight:bold; background:#f0fff0;" if item.get('es_total') else ""
            tabla_rows += f'''
            <tr style="{estilo} border-bottom:1px solid #eee;">
                <td style="padding:12px;">{icono} {item['campana']}</td>
                <td style="padding:12px; text-align:right;">{item['ejecutado']:,}</td>
                <td style="padding:12px; text-align:right;">{item['meta']:,}</td>
                <td style="padding:12px; text-align:right; font-weight:bold; color:{color_brecha};">{item['brecha']:+,}</td>
                <td style="padding:12px; text-align:right;">{item['cumplimiento_pct']}%</td>
            </tr>
            '''
        
        color_brecha_total = "#28a745" if brecha_total['brecha'] >= 0 else "#b61a23"
        estado_brecha = "✅ Superó la meta" if brecha_total['brecha'] >= 0 else f"❌ Faltan {abs(int(brecha_total['brecha'])):,} para la meta"
        prod_text = f" para <strong>{producto}</strong>" if producto else ""
        camp_text = f" en {campana}" if campana else ""
        fecha_text_display = f" al {fecha_display}" if fecha_limite else ""
        
        return f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3 style="color:#b61a23; margin:0 0 10px 0;">📊 Brecha{prod_text}{camp_text} - {aliado}{fecha_text_display}</h3>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px; margin:20px 0;">
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">Ejecutado</div>
                    <div style="font-size:24px; font-weight:bold; color:#333;">{brecha_total['ejecutado']:,.0f}</div>
                </div>
                <div style="text-align:center; padding:15px; background:#f5f5f5; border-radius:10px;">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">Meta</div>
                    <div style="font-size:24px; font-weight:bold; color:#333;">{brecha_total['meta']:,.0f}</div>
                </div>
                <div style="text-align:center; padding:15px; background:{color_brecha_total}15; border-radius:10px; border:2px solid {color_brecha_total};">
                    <div style="font-size:12px; color:#666; text-transform:uppercase;">Brecha</div>
                    <div style="font-size:24px; font-weight:bold; color:{color_brecha_total};">{brecha_total['brecha']:+,.0f}</div>
                </div>
            </div>
            <p style="text-align:center; font-size:16px; margin:15px 0; padding:10px; background:{color_brecha_total}15; border-radius:8px; color:{color_brecha_total};">
                <strong>{estado_brecha}</strong>
            </p>
            {grafica}
            <h4 style="color:#333; margin:20px 0 10px 0; border-bottom:2px solid #b61a23; padding-bottom:5px;">📋 Detalle por Campaña</h4>
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <thead>
                    <tr style="background-color:#b61a23; color:white;">
                        <th style="padding:12px; text-align:left;">Campaña</th>
                        <th style="padding:12px; text-align:right;">Ejecutado</th>
                        <th style="padding:12px; text-align:right;">Meta</th>
                        <th style="padding:12px; text-align:right;">Brecha</th>
                        <th style="padding:12px; text-align:right;">Cumplimiento</th>
                    </tr>
                </thead>
                <tbody>{tabla_rows}</tbody>
            </table>
            <div style="background:#f5f5f5; padding:15px; border-radius:8px; margin-top:20px; font-size:14px;">
                <p style="margin:0; color:#555;"><strong>🔍 Fórmula:</strong> Brecha = Ejecutado - Meta | <span style="color:#28a745;">✅ Verde:</span> Superó meta | <span style="color:#b61a23;">❌ Rojo:</span> Falta para meta</p>
            </div>
        </div>
        '''

    def _res_desempeno_especialista(self, nombre, mes):
        res = self.get_desempeno_por_especialista(nombre, mes)
        if not res: return f"<p>❌ Sin datos para {nombre}.</p>"
        total_altas = sum(r['ALTAS'] for r in res)
        total_ingresos = sum(r['INGRESOS'] for r in res)
        html = f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3 style="color:#b61a23; margin-top:0;">📊 Aliados de {nombre}</h3>
            <p style="color:#666; font-size:14px;">Mes: <strong>{mes}</strong></p>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin:20px 0;">
                <div style="background:#f5f5f5; padding:15px; border-radius:10px; text-align:center;">
                    <div style="font-size:12px; color:#666;">Total Altas</div>
                    <div style="font-size:24px; font-weight:bold; color:#b61a23;">{total_altas:,}</div>
                </div>
                <div style="background:#f5f5f5; padding:15px; border-radius:10px; text-align:center;">
                    <div style="font-size:12px; color:#666;">Total Ingresos</div>
                    <div style="font-size:24px; font-weight:bold; color:#0097a9;">${total_ingresos:,.0f}</div>
                </div>
            </div>
        '''
        headers = ['Aliado', 'Altas', 'Ingresos ($)']
        rows = [[r['ALIADO'], f"{int(r['ALTAS']):,}", f"${float(r['INGRESOS']):,.0f}"] for r in res]
        html += self._generate_html_table(headers, rows) + "</div>"
        return html

    def _res_desempeno_aliado(self, aliado, mes):
        res = self.get_desempeno_aliado(aliado, mes)
        if not res: return f"<p>❌ Sin datos para {aliado}.</p>"
        return f'''
        <div style="background:#fff; padding:20px; border-radius:10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #0097a9;">
            <h3 style="color:#b61a23; margin-top:0;">📊 {res['aliado']} en {res['mes']}</h3>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin:20px 0;">
                <div style="background:linear-gradient(135deg, #b61a23, #901219); color:white; padding:20px; border-radius:10px; text-align:center;">
                    <div style="font-size:12px; opacity:0.9;">Altas</div>
                    <div style="font-size:32px; font-weight:bold; margin:10px 0;">{res['altas']:,}</div>
                </div>
                <div style="background:linear-gradient(135deg, #0097a9, #007d8c); color:white; padding:20px; border-radius:10px; text-align:center;">
                    <div style="font-size:12px; opacity:0.9;">Ingresos</div>
                    <div style="font-size:32px; font-weight:bold; margin:10px 0;">${res['ingresos']:,.0f}</div>
                </div>
            </div>
        </div>
        '''

    def ask(self, question):
        question_clean = question.lower().strip()
        
        if any(x in question_clean for x in ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'hi', 'buen día']):
            return "<p>👋 ¡Hola! Soy Clara, tu asistente inteligente de ventas. ¿En qué puedo ayudarte hoy?</p>" + self._help_message()

        intent = self._detect_intent(question_clean)
        
        if not intent:
            aliado = self._extract_aliado(question_clean)
            if aliado:
                mes = self._extract_mes(question_clean) or self.get_current_month()
                return self._res_desempeno_aliado(aliado, mes)
            return self._help_message()

        mes = self._extract_mes(question_clean) or self.get_current_month()
        aliado = self._extract_aliado(question_clean)
        producto = self._extract_producto(question_clean)
        campana = self._extract_campana(question_clean)
        fecha_especifica = self._extract_fecha_especifica(question_clean)

        if intent == 'variacion':
            mes1, mes2 = self._extract_dos_meses(question_clean)
            if not mes1 or not mes2:
                mes1 = mes
                hoy = datetime.now()
                mes2 = f"{hoy.year-1}-12" if hoy.month == 1 else f"{hoy.year}-{(hoy.month-1):02d}"
            return self._handle_variacion_custom(aliado or "MILLENIUM", producto or "", mes1, mes2)

        elif intent == 'cumplimiento':
            if not aliado:
                return "<p>❌ Para ver el cumplimiento, indica un aliado (ej: ATENTO, COS, BRM o cualquier aliado de tus datos).</p>"
            if any(x in question_clean for x in ['grafica', 'gráfico', 'chart', 'visualizar']):
                return self._handle_cumplimiento_con_grafica(aliado, mes)
            return self._handle_cumplimiento_custom(aliado, mes)

        elif intent == 'ranking':
            return self._handle_ranking_custom(producto, mes, campana)

        elif intent == 'comportamiento':
            return self._handle_comportamiento_con_grafica()

        elif intent == 'producto_estrella':
            if not aliado:
                return "<p>❌ ¿De qué aliado quieres saber su producto estrella?</p>"
            return self._handle_producto_mas_vendido_custom(aliado, mes)

        elif intent == 'desempeno_especialista':
            especialista_found = next((esp for esp in self.especialistas.keys() if esp.lower() in question_clean), None)
            if especialista_found:
                return self._res_desempeno_especialista(especialista_found, mes)
            return "<p>❌ No identifiqué al especialista. Prueba con: Geovanny Ramirez, Cristian Villamil o Annie Solano.</p>"

        elif intent == 'desempeno_aliado':
            if not aliado:
                return "<p>❌ ¿De qué aliado quieres ver el desempeño?</p>"
            return self._res_desempeno_aliado(aliado, mes)

        elif intent == 'brecha':
            if not aliado:
                return "<p>❌ Para calcular brechas, indica un aliado.</p>"
            return self._handle_brecha_producto_aliado(aliado, producto, question_clean, campana)

        return self._help_message()