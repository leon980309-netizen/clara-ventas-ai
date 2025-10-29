import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import re
import json

# === FESTIVOS DE COLOMBIA (2024-2025) ===
CO_HOLIDAYS = {
    "2024-01-01", "2024-01-08", "2024-03-25", "2024-03-28", "2024-03-29",
    "2024-05-01", "2024-05-13", "2024-06-03", "2024-06-10", "2024-07-01",
    "2024-07-20", "2024-08-07", "2024-08-19", "2024-10-14", "2024-11-04",
    "2024-11-11", "2024-12-08", "2024-12-25",
    "2025-01-01", "2025-01-06", "2025-03-24", "2025-04-17", "2025-04-18",
    "2025-05-01", "2025-06-02", "2025-06-30", "2025-07-20", "2025-08-07",
    "2025-08-18", "2025-10-13", "2025-11-03", "2025-11-17", "2025-12-08", "2025-12-25"
}

def corregir_palabras(texto):
    correcciones = {
        'adiado': 'aliado', 'allado': 'aliado', 'aliad': 'aliado', 'aliados': 'aliado',
        'produto': 'producto', 'product': 'producto', 'productos': 'producto',
        'cumplimiendo': 'cumplimiento', 'cumplimieto': 'cumplimiento',
        'desempeno': 'desempeño', 'desempeño': 'desempeño',
        'meta': 'metas', 'metas': 'metas',
        'comparacion': 'comparativo', 'comparativo': 'comparativo',
        'ultimos': 'últimos', 'ultimo': 'último',
        'proyeccion': 'proyección', 'proyeccion': 'proyección',
        'ventas': 'ventas', 'venta': 'ventas',
    }
    palabras = texto.split()
    resultado = []
    for p in palabras:
        p_limpia = p.strip('.,;:!?¿¡"').lower()
        if p_limpia in correcciones:
            resultado.append(correcciones[p_limpia])
        else:
            corregido = p_limpia
            for mal, bien in correcciones.items():
                if len(p_limpia) >= 3 and mal.startswith(p_limpia[:3]):
                    corregido = bien
                    break
            resultado.append(corregido)
    return ' '.join(resultado)

def contar_dias_habiles(fecha_inicio, fecha_fin):
    dias = 0
    current = fecha_inicio
    while current <= fecha_fin:
        if current.weekday() < 5:  # Lunes a viernes
            if current.strftime("%Y-%m-%d") not in CO_HOLIDAYS:
                dias += 1
        current += timedelta(days=1)
    return dias

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
        self.sales_df = self.load_csv_from_url(url_consolidado)
        self.metas_df = self.load_csv_from_url(url_metas)
        print(f"✅ Clara IA: {len(self.sales_df)} filas cargadas")

    def clean_ingresos(self, series):
        if series.dtype == 'object':
            series = series.astype(str)
            series = series.str.replace(r'[$\s.]', '', regex=True)
            series = series.str.replace(',', '.', regex=False)
            def clean_val(x):
                if x in ['nan', '', '-', 'NaN']:
                    return '0'
                if x.count('.') > 1:
                    parts = x.split('.')
                    x = ''.join(parts[:-1]) + '.' + parts[-1]
                return x
            series = series.apply(clean_val)
            series = pd.to_numeric(series, errors='coerce')
        return series.fillna(0)

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
            df['INGRESOS'] = self.clean_ingresos(df['INGRESOS'])
        return df

    def extract_month_from_question(self, question):
        question_lower = question.lower()
        meses = {'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06',
                 'julio':'07','agosto':'08','septiembre':'09','octubre':'10','noviembre':'11','diciembre':'12'}
        for mes_nombre, mes_num in meses.items():
            if mes_nombre in question_lower:
                year_match = re.search(r'\b(202[45])\b', question)
                year = year_match.group(1) if year_match else '2025'
                return f"{year}-{mes_num}"
        return self.get_current_month()

    def get_current_month(self):
        if not self.sales_df.empty and 'Mes_Año' in self.sales_df.columns:
            return self.sales_df['Mes_Año'].max()
        return datetime.now().strftime('%Y-%m')

    def get_last_n_months(self, n=3):
        if self.sales_df.empty or 'Mes_Año' not in self.sales_df.columns:
            return []
        return sorted(self.sales_df['Mes_Año'].unique(), reverse=True)[:n]

    # === NUEVOS MÉTODOS ANALÍTICOS ===
    def get_top_aliado_por_producto(self, producto, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['BASE'].str.contains(producto, case=False, na=False)]
        if df_f.empty: return None
        top = df_f.groupby('ALIADO')['ALTAS'].sum().sort_values(ascending=False).head(1)
        aliado = top.index[0]
        altas = int(top.iloc[0])
        ingresos = float(df_f[df_f['ALIADO'] == aliado]['INGRESOS'].sum())
        return {'aliado': aliado, 'altas': altas, 'ingresos': ingresos, 'mes': mes}

    def get_producto_mas_vendido(self, periodo='mes'):
        if periodo == 'mes':
            mes = self.get_current_month()
            df = self.sales_df[self.sales_df['Mes_Año'] == mes]
        elif periodo == '3meses':
            meses = self.get_last_n_months(3)
            df = self.sales_df[self.sales_df['Mes_Año'].isin(meses)]
        elif periodo == 'anio':
            anio = datetime.now().year
            df = self.sales_df.copy()
            df['AÑO'] = pd.to_datetime(df['MES']).dt.year
            df = df[df['AÑO'] == anio]
        else:
            df = self.sales_df
        if df.empty: return None
        top = df.groupby('BASE')['ALTAS'].sum().sort_values(ascending=False).head(1)
        return {'producto': top.index[0], 'altas': int(top.iloc[0]), 'ingresos': float(df[df['BASE'] == top.index[0]]['INGRESOS'].sum())}

    def get_producto_menos_vendido(self, periodo='mes'):
        if periodo == 'mes':
            mes = self.get_current_month()
            df = self.sales_df[self.sales_df['Mes_Año'] == mes]
        elif periodo == '3meses':
            meses = self.get_last_n_months(3)
            df = self.sales_df[self.sales_df['Mes_Año'].isin(meses)]
        else:
            df = self.sales_df
        df = df[df['ALTAS'] > 0]
        if df.empty: return None
        bottom = df.groupby('BASE')['ALTAS'].sum().sort_values().head(1)
        return {'producto': bottom.index[0], 'altas': int(bottom.iloc[0]), 'ingresos': float(df[df['BASE'] == bottom.index[0]]['INGRESOS'].sum())}

    def get_comparativo_aliados_por_producto(self, producto, mes=None):
        if mes is None: mes = self.get_current_month()
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_f = df[df['BASE'].str.contains(producto, case=False, na=False)]
        if df_f.empty: return None
        res = df_f.groupby('ALIADO').agg({'ALTAS':'sum','INGRESOS':'sum'}).sort_values('ALTAS', ascending=False).reset_index()
        return res.to_dict(orient='records')

    def get_proyeccion_aliados(self, mes=None):
        if mes is None: mes = self.get_current_month()
        year, month = map(int, mes.split('-'))
        primer_dia = datetime(year, month, 1)
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if hoy.month != month or hoy.year != year:
            return None  # Solo mes actual
        ultimo_dia = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        dias_trans = contar_dias_habiles(primer_dia, min(hoy, ultimo_dia))
        dias_tot = contar_dias_habiles(primer_dia, ultimo_dia)
        if dias_trans == 0 or dias_tot == 0:
            return None

        # Ventas reales
        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        ventas = df.groupby('ALIADO').agg({'ALTAS':'sum','INGRESOS':'sum'}).reset_index()

        # Metas
        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        metas['Ingresos'] = metas['Ingresos'].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0')
        metas['Ingresos'] = pd.to_numeric(metas['Ingresos'], errors='coerce').fillna(0)
        metas_agg = metas.groupby('ALIADO').agg({'Altas':'sum','Ingresos':'sum'}).reset_index()

        # Proyección
        proj = pd.merge(ventas, metas_agg, on='ALIADO', how='outer').fillna(0)
        proj['PROY_ALTAS'] = (proj['ALTAS'] / dias_trans) * dias_tot
        proj['PROY_INGRESOS'] = (proj['INGRESOS'] / dias_trans) * dias_tot
        proj['PROY_ALTAS_%'] = (proj['PROY_ALTAS'] / proj['Altas'].replace(0, 1)) * 100
        proj['PROY_INGRESOS_%'] = (proj['PROY_INGRESOS'] / proj['Ingresos'].replace(0, 1)) * 100
        proj = proj.replace([float('inf'), -float('inf')], 0)
        return proj.to_dict(orient='records'), dias_trans, dias_tot

    # === MÉTODOS EXISTENTES ===
    def get_cumplimiento_detalle(self, aliado=None, producto=None, mes=None):
        if mes is None: mes = self.get_current_month()
        ventas = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        ventas['ALIADO'] = ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: ventas = ventas[ventas['ALIADO'] == aliado]
        if producto: ventas = ventas[ventas['BASE'].str.contains(producto, case=False, na=False)]
        ventas_reales = ventas.groupby('BASE').agg({'ALTAS':'sum','INGRESOS':'sum'}).reset_index()
        ventas_reales.columns = ['BASE', 'ALTAS_REALES', 'INGRESOS_REALES']

        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        if aliado: metas = metas[metas['ALIADO'] == aliado]
        if producto: metas = metas[metas['BASE'].str.contains(producto, case=False, na=False)]
        metas['Ingresos'] = metas['Ingresos'].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0')
        metas['Ingresos'] = pd.to_numeric(metas['Ingresos'], errors='coerce').fillna(0)
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

    def _generate_bar_chart_html(self, chart_id, labels, altas, ingresos):
        return f'''
        <div style="height:280px; margin:15px 0; position:relative;">
            <canvas id="{chart_id}" width="400" height="250"></canvas>
        </div>
        <script>
            (function() {{
                if (typeof Chart !== 'undefined') {{
                    const ctx = document.getElementById('{chart_id}').getContext('2d');
                    new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(labels)},
                            datasets: [
                                {{ label: 'Altas', data: {json.dumps(altas)}, backgroundColor: '#0078d4', yAxisID: 'y' }},
                                {{ label: 'Ingresos ($)', data: {json.dumps(ingresos)}, backgroundColor: '#e60000', yAxisID: 'y1' }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ position: 'top' }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            let label = context.dataset.label || '';
                                            if (label === 'Ingresos ($)') return label + ': $' + context.parsed.y.toLocaleString();
                                            return label + ': ' + context.parsed.y.toLocaleString();
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'Altas' }}, grid: {{ drawOnChartArea: false }} }},
                                y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Ingresos ($)' }}, grid: {{ drawOnChartArea: false }}, ticks: {{ callback: function(v) {{ return '$' + v.toLocaleString(); }} }} }}
                            }}
                        }}
                    }});
                }}
            }})();
        </script>
        '''

    def ask(self, question):
        question_norm = corregir_palabras(question.lower())
        question_lower = question_norm
        mes = self.extract_month_from_question(question)
        aliados_validos = ['COS', 'AQI', 'BRM', 'ATENTO', 'ABAI', 'MILLENIUM', 'NEXA', 'LATCOM', 'IBR', 'ALMACONTACT']

        # 🔹 PROYECCIÓN
        if "proyección" in question_lower or "proyeccion" in question_lower:
            if "últimos 3 meses" in question_lower or "ultimos 3 meses" in question_lower:
                return "<p>⚠️ La proyección solo está disponible para el mes en curso.</p>"
            try:
                resultado = self.get_proyeccion_aliados(mes)
                if not resultado:
                    return "<p>❌ No hay datos suficientes para calcular la proyección.</p>"
                datos, dias_trans, dias_tot = resultado
                headers = ['Aliado', 'Proy. Altas (%)', 'Proy. Ingresos (%)']
                rows = [[d['ALIADO'], f"{d['PROY_ALTAS_%']:.1f}%", f"{d['PROY_INGRESOS_%']:.1f}%"] for d in datos]
                tabla = self._generate_html_table(headers, rows)
                return f'''
                <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                    <h3 style="color:#e60000;">📈 Proyección de cumplimiento - {mes}</h3>
                    <p><strong>Días hábiles transcurridos:</strong> {dias_trans} de {dias_tot}</p>
                    <p><em>Proyección = (Ventas actuales / Días transcurridos) × Días totales del mes</em></p>
                </div>
                {tabla}
                '''
            except Exception as e:
                return f"<p>❌ Error en proyección: {str(e)}</p>"

        # 🔹 Aliado que más vendió un producto
        if ("aliado" in question_lower and ("más" in question_lower or "mas" in question_lower)) or "quién vendió más" in question_lower:
            productos = ['internet','terminales','ultra wifi','migraciones','portabilidad pospago','línea nueva','ug móvil','tecnología','adicionales','ug fijo','servicios fijo']
            for prod in productos:
                if prod in question_lower:
                    res = self.get_top_aliado_por_producto(prod, mes)
                    if res:
                        return f'''
                        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                            <h3 style="color:#e60000;">🏆 Aliado con más ventas de '{prod.title()}' en {res['mes']}</h3>
                            <p><strong>Aliado:</strong> {res['aliado']}</p>
                            <p><strong>Altas:</strong> {res['altas']:,}</p>
                            <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                        </div>
                        '''
                    else:
                        return f"<p>❌ No hay datos para <strong>{prod}</strong> en {mes}.</p>"

        # 🔹 Producto más/menos vendido
        if "producto más vendido" in question_lower or "producto mas vendido" in question_lower:
            periodo = '3meses' if "últimos 3 meses" in question_lower or "ultimos 3 meses" in question_lower else 'anio' if "año" in question_lower else 'mes'
            res = self.get_producto_mas_vendido(periodo)
            txt = "en los últimos 3 meses" if periodo=='3meses' else "en el año" if periodo=='anio' else f"en {mes}"
            if res:
                return f'''
                <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                    <h3 style="color:#e60000;">🔥 Producto más vendido {txt}</h3>
                    <p><strong>Producto:</strong> {res['producto']}</p>
                    <p><strong>Altas:</strong> {res['altas']:,}</p>
                    <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                </div>
                '''
            else:
                return f"<p>❌ No hay datos {txt}.</p>"

        if "producto menos vendido" in question_lower:
            periodo = '3meses' if "últimos 3 meses" in question_lower or "ultimos 3 meses" in question_lower else 'mes'
            res = self.get_producto_menos_vendido(periodo)
            txt = "en los últimos 3 meses" if periodo=='3meses' else f"en {mes}"
            if res:
                return f'''
                <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                    <h3 style="color:#e60000;">📉 Producto menos vendido {txt}</h3>
                    <p><strong>Producto:</strong> {res['producto']}</p>
                    <p><strong>Altas:</strong> {res['altas']:,}</p>
                    <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                </div>
                '''
            else:
                return f"<p>❌ No hay datos {txt}.</p>"

        # 🔹 Comparativo de aliados por producto
        if "comparativo" in question_lower and "aliado" in question_lower:
            productos = ['internet','terminales','ultra wifi','migraciones','portabilidad pospago','línea nueva','ug móvil','tecnología','adicionales','ug fijo','servicios fijo']
            for prod in productos:
                if prod in question_lower:
                    datos = self.get_comparativo_aliados_por_producto(prod, mes)
                    if datos:
                        headers = ['Aliado', 'Altas', 'Ingresos ($)']
                        rows = [[d['ALIADO'], f"{int(d['ALTAS']):,}", f"${float(d['INGRESOS']):,.0f}"] for d in datos]
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>📊 Comparativo de aliados en '{prod.title()}' ({mes})</h3>{tabla}"
                    else:
                        return f"<p>❌ No hay datos para <strong>{prod}</strong> en {mes}.</p>"

        # 🔹 Cumplimiento
        if "cumplimiento" in question_lower:
            aliado_encontrado = next((a for a in aliados_validos if a.lower() in question_lower), None)
            productos = ['internet','terminales','ultra wifi','migraciones','portabilidad pospago','línea nueva','ug móvil','tecnología','adicionales','ug fijo','servicios fijo']
            producto_encontrado = next((p for p in productos if p in question_lower), None)
            if aliado_encontrado:
                cumplimiento = self.get_cumplimiento_detalle(aliado_encontrado, producto_encontrado, mes)
                if cumplimiento:
                    if producto_encontrado:
                        item = cumplimiento[0]
                        return f'''
                        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                            <h3 style="color:#e60000;">🎯 Cumplimiento de {aliado_encontrado} en {producto_encontrado.title()} ({mes})</h3>
                            <p><strong>Altas:</strong> {int(item['ALTAS_REALES']):,} / {int(item['META_ALTAS']):,} → <strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong></p>
                            <p><strong>Ingresos:</strong> ${float(item['INGRESOS_REALES']):,.0f} / ${float(item['META_INGRESOS']):,.0f} → <strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong></p>
                        </div>
                        '''
                    else:
                        headers = ['Producto', 'Altas Reales', 'Meta Altas', 'Cumpl. Altas (%)', 'Ingresos Reales', 'Meta Ingresos', 'Cumpl. Ingresos (%)']
                        rows = [[item['BASE'], f"{int(item['ALTAS_REALES']):,}", f"{int(item['META_ALTAS']):,}", f"{item['CUMPLIMIENTO_ALTAS_%']}%", f"${float(item['INGRESOS_REALES']):,.0f}", f"${float(item['META_INGRESOS']):,.0f}", f"{item['CUMPLIMIENTO_INGRESOS_%']}%"] for item in cumplimiento]
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>🎯 Cumplimiento de {aliado_encontrado} por producto ({mes})</h3>{tabla}"
                else:
                    return f"<p>❌ No hay metas para <strong>{aliado_encontrado}</strong> en {mes}.</p>"

        # 🔹 Desempeño
        for aliado in aliados_validos:
            if aliado.lower() in question_lower and ('desempeño' in question_lower or 'desempeno' in question_lower):
                res = self.get_desempeno_aliado(aliado, mes)
                if res:
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">📊 {res['aliado']} en {res['mes']}</h3>
                        <p><strong>Altas:</strong> {res['altas']:,}</p>
                        <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                    </div>
                    '''
                else:
                    return f"<p>❌ No hay datos para <strong>{aliado}</strong> en {mes}.</p>"

        # ❓ Ayuda
        return '''
        <p>🤖 Puedes preguntarme:</p>
        <ul style="padding-left:20px; margin:10px 0;">
            <li>¿Cumplimiento del aliado ATENTO?</li>
            <li>¿Qué aliado vendió más Internet este mes?</li>
            <li>¿Cuál es el producto más vendido en los últimos 3 meses?</li>
            <li>¿Cuál es el producto menos vendido este mes?</li>
            <li>Comparativo de aliados en Servicios Fijo</li>
            <li>Dame la proyección de cumplimiento este mes</li>
            <li>Desempeño del aliado BRM en septiembre 2025</li>
        </ul>
        '''