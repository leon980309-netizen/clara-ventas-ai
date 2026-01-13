import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import re
import json

# Festivos de Colombia 2024-2025
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
            'ABAI Masivo': 'ABAI',
            'ABAI Proactivo': 'ABAI',
            'ABAI Segundo Anillo': 'ABAI',
            'ABAI Tercer Anillo': 'ABAI',
            'ABAI Whatsapp': 'ABAI',
            'Almacontact Swat': 'ALMACONTACT',
            'AQI  Segundo Anillo': 'AQI',
            'AQI Masivo Barranquilla': 'AQI',
            'AQI Tercer Anillo': 'AQI',
            'AQI Whatsapp': 'AQI',
            'Atento  Segundo Anillo': 'ATENTO',
            'Atento Clientes Criticos': 'ATENTO',
            'Atento Proactivo': 'ATENTO',
            'Atento Swat Bogotá': 'ATENTO',
            'Atento Traslados Pereira': 'ATENTO',
            'BRM Filtro': 'BRM',
            'BRM Masivo Medellín': 'BRM',
            'BRM Tercer Anillo': 'BRM',
            'BRM Whatsapp': 'BRM',
            'COS Fidelización Bogotá': 'COS',
            'COS Masivo Bogotá': 'COS',
            'COS Recuperación Bogotá': 'COS',
            'COS Segundo Anillo': 'COS',
            'COS Upselling': 'COS',
            'COS Whatsapp': 'COS',
            'IBR Latam SAC': 'IBR',
            'Latcom': 'LATCOM',
            'Millenium Masivo': 'MILLENIUM',
            'Millenium Web Center': 'MILLENIUM',
            'Nexa Masivo': 'NEXA'
        }
        self.especialistas = {
            'Cristian Villamil': ['COS', 'BRM'],
            'Annie Solano': ['AQI', 'MILLENIUM', 'ALMACONTACT', 'LATCOM'],
            'Geovanny Ramirez': ['NEXA', 'ABAI', 'ATENTO']
        }
        self.sales_df = self.load_csv_from_url(url_consolidado)
        self.metas_df = self.load_csv_from_url(url_metas)
        print(f"✅ Datos cargados: {len(self.sales_df)} filas")

    def load_csv_from_url(self, url):
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), sep=';', low_memory=False)
        if 'MES' in df.columns:
            df['MES'] = pd.to_datetime(df['MES'], format='%d/%m/%Y', errors='coerce')
            df = df.dropna(subset=['MES'])
            df['Mes_Año'] = df['MES'].dt.strftime('%Y-%m')
        if 'ALTAS' in df.columns:
            df['ALTAS'] = pd.to_numeric(df['ALTAS'], errors='coerce').fillna(0)
        if 'INGRESOS' in df.columns:
            df['INGRESOS'] = pd.to_numeric(
                df['INGRESOS'].astype(str)
                .str.replace(r'[$\s.]', '', regex=True)
                .str.replace(',', '.', regex=False),
                errors='coerce'
            ).fillna(0)
        return df

    def get_current_month(self):
        if not self.sales_df.empty and 'Mes_Año' in self.sales_df.columns:
            return self.sales_df['Mes_Año'].max()
        return datetime.now().strftime('%Y-%m')

    def get_last_n_months(self, n=3):
        if self.sales_df.empty or 'Mes_Año' not in self.sales_df.columns:
            return []
        return sorted(self.sales_df['Mes_Año'].unique(), reverse=True)[:n]

    def contar_dias_habiles(self, fecha_inicio, fecha_fin):
        dias = 0
        current = fecha_inicio
        while current <= fecha_fin:
            if current.weekday() < 5 and current.strftime("%Y-%m-%d") not in CO_HOLIDAYS:
                dias += 1
            current += timedelta(days=1)
        return dias

    # === MÉTODOS ANALÍTICOS (sin cambios) ===
    def get_desempeno_por_especialista(self, nombre_especialista, mes=None):
        if mes is None:
            mes = self.get_current_month()
        if nombre_especialista not in self.especialistas:
            return None
        aliados = self.especialistas[nombre_especialista]
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['ALIADO'].isin(aliados)]
        resumen = df_f.groupby('ALIADO').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reset_index()
        return resumen.to_dict(orient='records')

    def get_variacion_mes_a_mes(self, aliado, producto, mes1, mes2):
        df = self.sales_df.copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[
            (df['ALIADO'] == aliado) &
            (df['BASE'].str.contains(producto, case=False, na=False))
        ]
        ventas1 = df_f[df_f['Mes_Año'] == mes1]['ALTAS'].sum()
        ventas2 = df_f[df_f['Mes_Año'] == mes2]['ALTAS'].sum()
        if ventas2 == 0:
            variacion = float('inf') if ventas1 > 0 else 0
        else:
            variacion = ((ventas1 - ventas2) / ventas2) * 100
        return {
            'mes1': mes1,
            'mes2': mes2,
            'ventas1': int(ventas1),
            'ventas2': int(ventas2),
            'variacion_pct': round(variacion, 2)
        }

    def get_ranking_vendedores_por_producto(self, producto=None, mes=None):
        if mes is None:
            mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if producto:
            df = df[df['BASE'].str.contains(producto, case=False, na=False)]
        ranking = df.groupby(['ALIADO', 'CAMPAÑA FINAL']).agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reset_index().sort_values('ALTAS', ascending=False)
        return ranking.to_dict(orient='records')

    def get_comportamiento_total_operacion(self):
        meses = self.get_last_n_months(3)
        df = self.sales_df[self.sales_df['Mes_Año'].isin(meses)].copy()
        total = df.groupby('Mes_Año').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reindex(meses, fill_value=0).reset_index()
        return total.to_dict(orient='records')

    def get_producto_mas_vendido_por_aliado(self, aliado, mes=None):
        if mes is None:
            mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['ALIADO'] == aliado]
        if df_f.empty:
            return None
        top = df_f.groupby('BASE')['ALTAS'].sum().sort_values(ascending=False).head(1)
        return {
            'aliado': aliado,
            'producto': top.index[0],
            'altas': int(top.iloc[0]),
            'mes': mes
        }

    def get_top_aliado_por_producto(self, producto, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['BASE'].str.contains(producto, case=False, na=False, regex=False)]
        if df_f.empty: return None
        top = df_f.groupby('ALIADO')['ALTAS'].sum().sort_values(ascending=False).head(1)
        aliado = top.index[0]
        altas = int(top.iloc[0])
        ingresos = float(df_f[df_f['ALIADO'] == aliado]['INGRESOS'].sum())
        return {'aliado': aliado, 'altas': altas, 'ingresos': ingresos, 'mes': mes}

    def get_cumplimiento_detalle(self, aliado=None, producto=None, mes=None):
        if mes is None: mes = self.get_current_month()
        ventas = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        ventas['ALIADO'] = ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: ventas = ventas[ventas['ALIADO'] == aliado]
        if producto: ventas = ventas[ventas['BASE'].str.contains(producto, case=False, na=False, regex=False)]
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
        metas['Ingresos'] = pd.to_numeric(
            metas['Ingresos'].astype(str)
            .str.replace(r'[$\s.]', '', regex=True)
            .replace('-', '0'),
            errors='coerce'
        ).fillna(0)
        metas_reales = metas.groupby('BASE').agg({'Altas':'sum','Ingresos':'sum'}).reset_index()
        metas_reales.columns = ['BASE', 'META_ALTAS', 'META_INGRESOS']

        cumplimiento = pd.merge(ventas_reales, metas_reales, on='BASE', how='outer').fillna(0)
        cumplimiento['CUMPLIMIENTO_ALTAS_%'] = round((cumplimiento['ALTAS_REALES'] / cumplimiento['META_ALTAS'].replace(0,1)) * 100, 2)
        cumplimiento['CUMPLIMIENTO_INGRESOS_%'] = round((cumplimiento['INGRESOS_REALES'] / cumplimiento['META_INGRESOS'].replace(0,1)) * 100, 2)
        cumplimiento = cumplimiento.replace([float('inf'), -float('inf')], 0)
        return cumplimiento.to_dict(orient='records')

    def get_desempeno_aliado(self, aliado, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df = df[df['ALIADO'] == aliado]
        if df.empty: return None
        return {'aliado': aliado, 'mes': mes, 'altas': int(df['ALTAS'].sum()), 'ingresos': float(df['INGRESOS'].sum())}

    def _generate_html_table(self, headers, rows):
        html = '<table style="width:100%; border-collapse: collapse; margin: 10px 0; font-size: 14px;">'
        html += '<thead><tr style="background-color:#e60000; color:white;">'
        for h in headers: html += f'<th style="padding:10px; text-align:left;">{h}</th>'
        html += '</tr></thead><tbody>'
        for row in rows:
            html += '<tr style="border-bottom:1px solid #eee;">'
            for cell in row: html += f'<td style="padding:10px;">{cell}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        return html

    # === NUEVOS MÉTODOS AUXILIARES PARA INTERPRETACIÓN DINÁMICA ===
    def _extract_aliado(self, text):
        for aliado in self.homologacion_aliados.values():
            if aliado.lower() in text:
                return aliado
        for campana, aliado in self.homologacion_aliados.items():
            if campana.lower() in text:
                return aliado
        return None

    def _extract_producto(self, text):
        if "fijo" in text:
            return "fijo"
        elif "móvil" in text or "movil" in text:
            return "m"
        else:
            return None

    def _extract_mes(self, text):
        meses_nombres = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        pattern = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mes_nombre = match.group(1).lower()
            anio = match.group(2)
            mes_num = meses_nombres.get(mes_nombre, "01")
            return f"{anio}-{mes_num}"
        return None

    def _extract_dos_meses(self, text):
        meses_nombres = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        pattern = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(\d{4}).*?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            m1, a1, m2, a2 = match.groups()
            mes1 = f"{a1}-{meses_nombres.get(m1.lower(), '01')}"
            mes2 = f"{a2}-{meses_nombres.get(m2.lower(), '01')}"
            return mes1, mes2
        return None, None

    # === MANEJADORES DE CONSULTAS ===
    def _handle_variacion(self, text):
        aliado = self._extract_aliado(text) or "MILLENIUM"
        producto = self._extract_producto(text) or "m"
        mes1, mes2 = self._extract_dos_meses(text)
        if not mes1 or not mes2:
            return "<p>❌ Por favor, indica dos meses completos (ej: 'agosto 2025 vs julio 2025').</p>"
        res = self.get_variacion_mes_a_mes(aliado, producto, mes1, mes2)
        if res['ventas1'] == 0 and res['ventas2'] == 0:
            return f"<p>❌ No hay datos de ventas para '{producto}' en {aliado} en esos meses.</p>"
        analisis = f"<p><strong>🔍 Análisis:</strong> La variación de <strong>{res['variacion_pct']:+.2f}%</strong> en {aliado} indica {'crecimiento' if res['variacion_pct'] > 0 else 'caída'} en ventas de {producto}.</p>"
        return f'''
        <div><h3>📊 Variación {producto} - {aliado}</h3>
        <p><strong>{res['mes1']}</strong>: {res['ventas1']:,} altas</p>
        <p><strong>{res['mes2']}</strong>: {res['ventas2']:,} altas</p>
        <p><strong>Variación:</strong> {res['variacion_pct']:+.2f}%</p>{analisis}</div>
        '''

    def _handle_cumplimiento(self, text):
        aliado = self._extract_aliado(text)
        mes = self._extract_mes(text) or self.get_current_month()
        if not aliado:
            return "<p>❌ Indica un aliado (ej: ATENTO, COS, BRM).</p>"
        cumplimiento = self.get_cumplimiento_detalle(aliado=aliado, mes=mes)
        if not cumplimiento or all(item['ALTAS_REALES'] == 0 and item['META_ALTAS'] == 0 for item in cumplimiento):
            return f"<p>❌ No hay datos de cumplimiento para {aliado} en {mes}.</p>"
        item = cumplimiento[0]
        analisis = f"<p><strong>🔍 Análisis:</strong> {aliado} tiene <strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong> en altas y <strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong> en ingresos.</p>"
        return f'''
        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
            <h3 style="color:#e60000;">🎯 Cumplimiento de {aliado} en {mes}</h3>
            <p><strong>Altas:</strong> {int(item['ALTAS_REALES']):,} / {int(item['META_ALTAS']):,} → <strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong></p>
            <p><strong>Ingresos:</strong> ${float(item['INGRESOS_REALES']):,.0f} / ${float(item['META_INGRESOS']):,.0f} → <strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong></p>
            {analisis}
        </div>
        '''

    def _handle_ranking(self, text):
        producto = self._extract_producto(text)
        mes = self._extract_mes(text) or self.get_current_month()
        ranking = self.get_ranking_vendedores_por_producto(producto=producto, mes=mes)
        if not ranking:
            return "<p>❌ No hay datos para el ranking solicitado.</p>"
        top_aliado = ranking[0]['ALIADO']
        analisis = f"<p><strong>🔍 Análisis:</strong> <strong>{top_aliado}</strong> lidera con <strong>{int(ranking[0]['ALTAS']):,} altas</strong>.</p>"
        headers = ['Aliado', 'Campaña', 'Altas', 'Ingresos ($)']
        rows = [[r['ALIADO'], r['CAMPAÑA FINAL'], f"{int(r['ALTAS']):,}", f"${float(r['INGRESOS']):,.0f}"] for r in ranking[:10]]
        tabla = self._generate_html_table(headers, rows)
        prod_text = f" para {producto}" if producto else ""
        return f"<h3>🏆 Ranking de vendedores{prod_text} en {mes}</h3>{tabla}{analisis}"

    def _handle_comportamiento_total(self):
        datos = self.get_comportamiento_total_operacion()
        if not datos:
            return "<p>❌ No hay datos para los últimos 3 meses.</p>"
        total_ingresos = sum(d['INGRESOS'] for d in datos)
        analisis = f"<p><strong>🔍 Análisis:</strong> La operación acumula <strong>${total_ingresos:,.0f} en ingresos</strong> en los últimos 3 meses.</p>"
        headers = ['Mes', 'Altas', 'Ingresos ($)']
        rows = [[d['Mes_Año'], f"{int(d['ALTAS']):,}", f"${float(d['INGRESOS']):,.0f}"] for d in datos]
        tabla = self._generate_html_table(headers, rows)
        return f"<h3>📈 Comportamiento total - Últimos 3 meses</h3>{tabla}{analisis}"

    def _handle_producto_mas_vendido(self, text):
        aliado = self._extract_aliado(text)
        mes = self._extract_mes(text) or self.get_current_month()
        if not aliado:
            return "<p>❌ Indica un aliado (ej: COS, ATENTO).</p>"
        res = self.get_producto_mas_vendido_por_aliado(aliado, mes)
        if not res:
            return f"<p>❌ No hay ventas registradas para {aliado} en {mes}.</p>"
        analisis = f"<p><strong>🔍 Análisis:</strong> <strong>{res['producto']}</strong> es el producto estrella de <strong>{aliado}</strong>, con <strong>{res['altas']:,} altas</strong>.</p>"
        return f"<p>🔥 El producto más vendido por <strong>{aliado}</strong> en {res['mes']} es <strong>{res['producto']}</strong> con {res['altas']:,} altas.</p>{analisis}"

    def _res_desempeno_especialista(self, nombre, mes):
        res = self.get_desempeno_por_especialista(nombre, mes)
        if not res:
            return f"<p>❌ No hay datos para los aliados de {nombre} en {mes}.</p>"
        total_altas = sum(r['ALTAS'] for r in res)
        total_ingresos = sum(r['INGRESOS'] for r in res)
        analisis = f"<p><strong>🔍 Análisis:</strong> Los aliados de {nombre} generan <strong>{total_altas:,} altas</strong> y <strong>${total_ingresos:,.0f} en ingresos</strong>.</p>"
        headers = ['Aliado', 'Altas', 'Ingresos ($)']
        rows = [[r['ALIADO'], f"{int(r['ALTAS']):,}", f"${float(r['INGRESOS']):,.0f}"] for r in res]
        tabla = self._generate_html_table(headers, rows)
        return f"<h3>📊 Desempeño de aliados de <strong>{nombre}</strong> en {mes}</h3>{tabla}{analisis}"

    def _res_desempeno_aliado(self, aliado, mes):
        res = self.get_desempeno_aliado(aliado, mes)
        if not res:
            return f"<p>❌ No hay datos para {aliado} en {mes}.</p>"
        analisis = f"<p><strong>🔍 Análisis:</strong> {aliado} muestra un desempeño sólido con <strong>{res['altas']:,} altas</strong> y <strong>${res['ingresos']:,.0f} en ingresos</strong>.</p>"
        return f'''
        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
            <h3 style="color:#e60000;">📊 {res['aliado']} en {res['mes']}</h3>
            <p><strong>Altas:</strong> {res['altas']:,}</p>
            <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
            {analisis}
        </div>
        '''

    def _help_message(self):
        return '''
        <p>🤖 Puedes preguntarme de forma flexible, por ejemplo:</p>
        <ul style="padding-left:20px; margin:10px 0;">
            <li>“Variación de móvil en ATENTO entre septiembre 2025 y agosto 2025”</li>
            <li>“Cumplimiento de COS en octubre 2024”</li>
            <li>“Ranking de vendedores para fijo en noviembre 2025”</li>
            <li>“Producto más vendido por BRM en diciembre 2025”</li>
            <li>“Desempeño de Geovanny Ramirez en enero 2026”</li>
        </ul>
        '''

    # === MÉTODO ASK DINÁMICO (REEMPLAZA EL ANTERIOR) ===
    def ask(self, question):
        question_clean = question.lower().strip()

        # Detectar tipo de consulta
        if any(kw in question_clean for kw in ["variacion", "variación", "cambio", "diferencia"]):
            return self._handle_variacion(question_clean)
        elif any(kw in question_clean for kw in ["cumplimiento", "meta", "objetivo"]):
            return self._handle_cumplimiento(question_clean)
        elif any(kw in question_clean for kw in ["ranking", "top", "mayores vendedores", "mejores vendedores"]):
            return self._handle_ranking(question_clean)
        elif any(kw in question_clean for kw in ["comportamiento total", "totales", "últimos 3 meses", "ultimos 3 meses", "últimos tres meses"]):
            return self._handle_comportamiento_total()
        elif any(kw in question_clean for kw in ["producto más vendido", "producto mas vendido", "estrella", "más vendido"]):
            return self._handle_producto_mas_vendido(question_clean)
        elif "geovanny ramirez" in question_clean or "geovany ramirez" in question_clean:
            mes = self._extract_mes(question_clean) or self.get_current_month()
            return self._res_desempeno_especialista("Geovanny Ramirez", mes)
        elif any(kw in question_clean for kw in ["desempeño", "desempeno", "rendimiento"]) and any(a.lower() in question_clean for a in self.homologacion_aliados.values()):
            aliado = self._extract_aliado(question_clean)
            mes = self._extract_mes(question_clean) or self.get_current_month()
            if aliado:
                return self._res_desempeno_aliado(aliado, mes)

        return self._help_message()