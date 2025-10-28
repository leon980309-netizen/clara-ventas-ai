import pandas as pd
import os
import requests
from io import StringIO
from datetime import datetime
import re
import json

class ClaraIA:
    def __init__(self, url_consolidado, url_metas):
        # ✅ Homologación EXACTA según tu lista
        self.homologacion_aliados = {
            'ABAI Masivo': 'ABAI',
            'ABAI Proactivo': 'ABAI',
            'ABAI Segundo Anillo': 'ABAI',
            'ABAI Tercer Anillo': 'ABAI',
            'ABAI Whatsapp': 'ABAI',
            'Almacontact Swat': 'ALMACONTACT',
            'AQI  Segundo Anillo': 'AQI',          # Dos espacios
            'AQI Masivo Barranquilla': 'AQI',
            'AQI Tercer Anillo': 'AQI',
            'AQI Whatsapp': 'AQI',
            'Atento  Segundo Anillo': 'ATENTO',    # Dos espacios
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
        print(f"✅ Datos cargados: {len(self.sales_df)} filas en ventas")

    def clean_ingresos(self, series):
        if series.dtype == 'object':
            series = series.astype(str)
            series = series.str.replace(r'[$\s.]', '', regex=True)
            series = series.str.replace(',', '.', regex=False)
            def clean_val(x):
                if x == 'nan' or x == '' or x == '-':
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
        """Extrae el mes de la pregunta (ej. 'septiembre 2025' → '2025-09')."""
        question_lower = question.lower()
        
        # Meses en español
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        for mes_nombre, mes_num in meses.items():
            if mes_nombre in question_lower:
                # Buscar año cercano (2024 o 2025)
                year_match = re.search(r'\b(202[45])\b', question)
                year = year_match.group(1) if year_match else '2025'
                return f"{year}-{mes_num}"
        
        # Si no se especifica, usar el mes actual
        return self.get_current_month()

    def get_current_month(self):
        if not self.sales_df.empty and 'Mes_Año' in self.sales_df.columns:
            return self.sales_df['Mes_Año'].max()
        return datetime.now().strftime('%Y-%m')

    def get_last_n_months(self, n=3):
        """Obtiene los últimos N meses con datos."""
        if self.sales_df.empty or 'Mes_Año' not in self.sales_df.columns:
            return []
        meses = sorted(self.sales_df['Mes_Año'].unique(), reverse=True)
        return meses[:n]

    def get_comparativo_aliado_3meses(self, aliado):
        """Devuelve datos de los últimos 3 meses para un aliado."""
        meses = self.get_last_n_months(3)
        df = self.sales_df.copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_filtrado = df[(df['ALIADO'] == aliado) & (df['Mes_Año'].isin(meses))]

        resumen = df_filtrado.groupby('Mes_Año').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reindex(meses, fill_value=0).reset_index()

        return resumen.to_dict(orient='records')

    def get_comparativo_producto_3meses(self, producto):
        """Devuelve datos de los últimos 3 meses para un producto (BASE)."""
        meses = self.get_last_n_months(3)
        df = self.sales_df.copy()
        df_filtrado = df[
            (df['BASE'].str.contains(producto, case=False, na=False)) &
            (df['Mes_Año'].isin(meses))
        ]

        resumen = df_filtrado.groupby('Mes_Año').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reindex(meses, fill_value=0).reset_index()

        return resumen.to_dict(orient='records')

    def get_mejor_mes_anio(self):
        """Devuelve el mes con mayores ingresos en el año actual."""
        anio_actual = datetime.now().year
        df = self.sales_df.copy()
        if 'MES' not in df.columns:
            return None
        df['AÑO'] = pd.to_datetime(df['MES']).dt.year
        df_anio = df[df['AÑO'] == anio_actual]

        mejor_mes = df_anio.groupby('Mes_Año').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).sort_values('INGRESOS', ascending=False).head(1)

        if mejor_mes.empty:
            return None
        mes = mejor_mes.index[0]
        altas = int(mejor_mes['ALTAS'].iloc[0])
        ingresos = float(mejor_mes['INGRESOS'].iloc[0])
        return {'mes': mes, 'altas': altas, 'ingresos': ingresos}

    # 🔹 Cumplimiento detallado por aliado y/o producto
    def get_cumplimiento_detalle(self, aliado=None, producto=None, mes=None):
        if mes is None:
            mes = self.get_current_month()
        
        # --- Ventas reales ---
        ventas = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        ventas['ALIADO'] = ventas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        
        if aliado:
            ventas = ventas[ventas['ALIADO'] == aliado]
        if producto:
            ventas = ventas[ventas['BASE'].str.contains(producto, case=False, na=False)]
        
        ventas_reales = ventas.groupby('BASE').agg({
            'ALTAS': 'sum',
            'INGRESOS': 'sum'
        }).reset_index()
        ventas_reales.columns = ['BASE', 'ALTAS_REALES', 'INGRESOS_REALES']
        
        # --- Metas ---
        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        
        if aliado:
            metas = metas[metas['ALIADO'] == aliado]
        if producto:
            metas = metas[metas['BASE'].str.contains(producto, case=False, na=False)]
        
        # Limpiar ingresos en metas
        metas['Ingresos'] = metas['Ingresos'].astype(str).str.replace(r'[$\s.]', '', regex=True).replace('-', '0')
        metas['Ingresos'] = pd.to_numeric(metas['Ingresos'], errors='coerce').fillna(0)
        
        metas_reales = metas.groupby('BASE').agg({
            'Altas': 'sum',
            'Ingresos': 'sum'
        }).reset_index()
        metas_reales.columns = ['BASE', 'META_ALTAS', 'META_INGRESOS']
        
        # --- Combinar ---
        cumplimiento = pd.merge(ventas_reales, metas_reales, on='BASE', how='outer').fillna(0)
        cumplimiento['CUMPLIMIENTO_ALTAS_%'] = round((cumplimiento['ALTAS_REALES'] / cumplimiento['META_ALTAS']) * 100, 2)
        cumplimiento['CUMPLIMIENTO_INGRESOS_%'] = round((cumplimiento['INGRESOS_REALES'] / cumplimiento['META_INGRESOS']) * 100, 2)
        cumplimiento = cumplimiento.replace([float('inf'), -float('inf')], 0)
        
        return cumplimiento.to_dict(orient='records')

    # 🔹 Metas por producto de una campaña
    def get_metas_por_producto_campana(self, campana, mes=None):
        if mes is None:
            mes = self.get_current_month()
        
        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas_filtradas = metas[metas['CAMPAÑA FINAL'] == campana]
        
        if metas_filtradas.empty:
            return None
        
        resumen = metas_filtradas.groupby('BASE').agg({
            'Altas': 'sum',
            'Ingresos': lambda x: x.str.replace(r'[$\s.]', '', regex=True).replace('-', '0').astype(float).sum()
        }).reset_index()
        
        return {
            'tipo': 'campaña',
            'nombre': campana,
            'mes': mes,
            'productos': resumen.to_dict(orient='records')
        }

    # 🔹 Metas por producto de un aliado
    def get_metas_por_producto_aliado(self, aliado, mes=None):
        if mes is None:
            mes = self.get_current_month()
        
        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        metas_filtradas = metas[metas['ALIADO'] == aliado]
        
        if metas_filtradas.empty:
            return None
        
        resumen = metas_filtradas.groupby('BASE').agg({
            'Altas': 'sum',
            'Ingresos': lambda x: x.str.replace(r'[$\s.]', '', regex=True).replace('-', '0').astype(float).sum()
        }).reset_index()
        
        return {
            'tipo': 'aliado',
            'nombre': aliado,
            'mes': mes,
            'productos': resumen.to_dict(orient='records')
        }

    # 🔹 Desempeño por aliado (ventas reales)
    def get_desempeno_aliado(self, aliado, mes=None):
        if mes is None:
            mes = self.get_current_month()
        df_mes = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df_mes['ALIADO'] = df_mes['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_filtrado = df_mes[df_mes['ALIADO'] == aliado]
        if df_filtrado.empty:
            return None
        return {
            'aliado': aliado,
            'mes': mes,
            'altas': int(df_filtrado['ALTAS'].sum()),
            'ingresos': float(df_filtrado['INGRESOS'].sum())
        }

    # 🔹 Desempeño por campaña (ventas reales)
    def get_desempeno_campana(self, campana, mes=None):
        if mes is None:
            mes = self.get_current_month()
        df_mes = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df_filtrado = df_mes[df_mes['CAMPAÑA FINAL'] == campana]
        if df_filtrado.empty:
            return None
        return {
            'campana': campana,
            'mes': mes,
            'altas': int(df_filtrado['ALTAS'].sum()),
            'ingresos': float(df_filtrado['INGRESOS'].sum())
        }

    def _generate_html_table(self, headers, rows):
        """Genera una tabla HTML limpia."""
        html = '<table style="width:100%; border-collapse: collapse; margin: 10px 0; font-size: 14px;">'
        html += '<thead><tr style="background-color:#e60000; color:white;">'
        for h in headers:
            html += f'<th style="padding:10px; text-align:left;">{h}</th>'
        html += '</tr></thead><tbody>'
        for row in rows:
            html += '<tr style="border-bottom:1px solid #eee;">'
            for cell in row:
                html += f'<td style="padding:10px;">{cell}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        return html

    def _generate_bar_chart_html(self, chart_id, labels, altas, ingresos):
        """Genera un gráfico de barras con Chart.js (HTML + JS)."""
        chart_html = f'''
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
                                {{
                                    label: 'Altas',
                                    data: {json.dumps(altas)},
                                    backgroundColor: '#0078d4',
                                    yAxisID: 'y'
                                }},
                                {{
                                    label: 'Ingresos ($)',
                                    data: {json.dumps(ingresos)},
                                    backgroundColor: '#e60000',
                                    yAxisID: 'y1'
                                }}
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
                                            if (label === 'Ingresos ($)') {{
                                                return label + ': $' + context.parsed.y.toLocaleString();
                                            }}
                                            return label + ': ' + context.parsed.y.toLocaleString();
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                y: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    title: {{ display: true, text: 'Altas' }},
                                    grid: {{ drawOnChartArea: false }}
                                }},
                                y1: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: {{ display: true, text: 'Ingresos ($)' }},
                                    grid: {{ drawOnChartArea: false }},
                                    ticks: {{
                                        callback: function(value) {{
                                            return '$' + value.toLocaleString();
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
            }})();
        </script>
        '''
        return chart_html

    def ask(self, question):
        question_lower = question.lower()
        mes = self.extract_month_from_question(question)
        aliados_validos = ['COS', 'AQI', 'BRM', 'ATENTO', 'ABAI', 'MILLENIUM', 'NEXA', 'LATCOM', 'IBR', 'ALMACONTACT']

        # 🔹 Comparativo últimos 3 meses por aliado
        if ("últimos 3 meses" in question_lower or "ultimos 3 meses" in question_lower):
            for aliado in aliados_validos:
                if aliado.lower() in question_lower:
                    datos = self.get_comparativo_aliado_3meses(aliado)
                    if datos:
                        labels = [d['Mes_Año'] for d in datos]
                        altas = [int(d['ALTAS']) for d in datos]
                        ingresos = [float(d['INGRESOS']) for d in datos]

                        headers = ['Mes', 'Altas', 'Ingresos ($)']
                        rows = [[d['Mes_Año'], f"{int(d['ALTAS']):,}", f"${float(d['INGRESOS']):,.0f}"] for d in datos]
                        tabla = self._generate_html_table(headers, rows)
                        chart_id = f"chart_{aliado.replace(' ', '_').replace('-', '_')}"
                        grafico = self._generate_bar_chart_html(chart_id, labels, altas, ingresos)
                        return f"<h3 style='color:#e60000;'>📊 Comparativo de {aliado} - Últimos 3 meses</h3>{tabla}{grafico}"
                    else:
                        return f"<p>❌ No hay datos para <strong>{aliado}</strong> en los últimos 3 meses.</p>"

            # Por producto
            productos_posibles = [
                'internet', 'terminales', 'ultra wifi', 'migraciones', 'portabilidad pospago',
                'línea nueva', 'ug móvil', 'tecnología', 'adicionales', 'ug fijo', 'servicios fijo'
            ]
            for prod in productos_posibles:
                if prod in question_lower:
                    datos = self.get_comparativo_producto_3meses(prod)
                    if datos:
                        labels = [d['Mes_Año'] for d in datos]
                        altas = [int(d['ALTAS']) for d in datos]
                        ingresos = [float(d['INGRESOS']) for d in datos]

                        headers = ['Mes', 'Altas', 'Ingresos ($)']
                        rows = [[d['Mes_Año'], f"{int(d['ALTAS']):,}", f"${float(d['INGRESOS']):,.0f}"] for d in datos]
                        tabla = self._generate_html_table(headers, rows)
                        chart_id = f"chart_prod_{prod.replace(' ', '_').replace('í', 'i')}"
                        grafico = self._generate_bar_chart_html(chart_id, labels, altas, ingresos)
                        return f"<h3 style='color:#e60000;'>📊 Comparativo de '{prod.title()}' - Últimos 3 meses</h3>{tabla}{grafico}"
                    else:
                        return f"<p>❌ No hay datos para el producto <strong>{prod}</strong> en los últimos 3 meses.</p>"

        # 🔹 Mejor mes del año
        if "mejor mes" in question_lower and ("año" in question_lower or "anio" in question_lower or "2025" in question_lower or "2024" in question_lower):
            mejor = self.get_mejor_mes_anio()
            if mejor:
                return f'''
                <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                    <h3 style="color:#e60000;">🏆 Mejor mes del año ({datetime.now().year})</h3>
                    <p><strong>Mes:</strong> {mejor['mes']}</p>
                    <p><strong>Altas:</strong> {mejor['altas']:,}</p>
                    <p><strong>Ingresos:</strong> ${mejor['ingresos']:,.0f}</p>
                </div>
                '''
            else:
                return "<p>❌ No hay datos suficientes para determinar el mejor mes del año.</p>"

        # 🔹 Cumplimiento detallado
        if "cumplimiento" in question_lower:
            aliado_encontrado = None
            producto_encontrado = None
            
            for aliado in aliados_validos:
                if aliado.lower() in question_lower:
                    aliado_encontrado = aliado
                    break
            
            productos_posibles = [
                'internet', 'terminales', 'ultra wifi', 'migraciones', 'portabilidad pospago',
                'línea nueva', 'ug móvil', 'tecnología', 'adicionales', 'ug fijo', 'servicios fijo'
            ]
            for prod in productos_posibles:
                if prod in question_lower:
                    producto_encontrado = prod
                    break
            
            if aliado_encontrado:
                cumplimiento = self.get_cumplimiento_detalle(
                    aliado=aliado_encontrado,
                    producto=producto_encontrado,
                    mes=mes
                )
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
                        rows = []
                        for item in cumplimiento:
                            rows.append([
                                item['BASE'],
                                f"{int(item['ALTAS_REALES']):,}",
                                f"{int(item['META_ALTAS']):,}",
                                f"{item['CUMPLIMIENTO_ALTAS_%']}%",
                                f"${float(item['INGRESOS_REALES']):,.0f}",
                                f"${float(item['META_INGRESOS']):,.0f}",
                                f"{item['CUMPLIMIENTO_INGRESOS_%']}%"
                            ])
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>🎯 Cumplimiento de {aliado_encontrado} por producto ({mes})</h3>{tabla}"
                else:
                    return f"<p>❌ No hay datos de metas para <strong>{aliado_encontrado}</strong> en {mes}.</p>"

        # 🔹 Metas de una campaña
        if "meta" in question_lower or "metas" in question_lower:
            for campana in self.sales_df['CAMPAÑA FINAL'].dropna().unique():
                if campana.lower() in question_lower:
                    metas = self.get_metas_por_producto_campana(campana, mes)
                    if metas:
                        headers = ['Producto', 'Altas', 'Ingresos ($)']
                        rows = [[prod['BASE'], f"{int(prod['Altas']):,}", f"${float(prod['Ingresos']):,.0f}"] for prod in metas['productos']]
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>🎯 Metas de la campaña '{campana}' en {mes}</h3>{tabla}"
                    else:
                        return f"<p>❌ No hay metas para la campaña <strong>{campana}</strong> en {mes}.</p>"

            # Metas por aliado
            for aliado in aliados_validos:
                if aliado.lower() in question_lower:
                    metas = self.get_metas_por_producto_aliado(aliado, mes)
                    if metas:
                        headers = ['Producto', 'Altas', 'Ingresos ($)']
                        rows = [[prod['BASE'], f"{int(prod['Altas']):,}", f"${float(prod['Ingresos']):,.0f}"] for prod in metas['productos']]
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>🎯 Metas de {aliado} en {mes}</h3>{tabla}"
                    else:
                        return f"<p>❌ No hay metas para <strong>{aliado}</strong> en {mes}.</p>"

        # 🔹 Desempeño por aliado
        for aliado in aliados_validos:
            if aliado.lower() in question_lower and ('desempeño' in question_lower or 'aliado' in question_lower or 'desempeno' in question_lower):
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

        # 🔹 Desempeño por campaña
        if "campaña" in question_lower or "campana" in question_lower:
            for campana in self.sales_df['CAMPAÑA FINAL'].dropna().unique():
                if campana.lower() in question_lower:
                    res = self.get_desempeno_campana(campana, mes)
                    if res:
                        return f'''
                        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                            <h3 style="color:#e60000;">📢 Campaña: {res['campana']} en {res['mes']}</h3>
                            <p><strong>Altas:</strong> {res['altas']:,}</p>
                            <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                        </div>
                        '''
            return "<p>❌ No encontré esa campaña.</p>"

        # ❓ Ayuda
        return '''
        <p>🤖 Puedes preguntarme:</p>
        <ul style="padding-left:20px; margin:10px 0;">
            <li>¿Cumplimiento del aliado ATENTO?</li>
            <li>¿Metas de la campaña COS Masivo Bogotá en septiembre 2025?</li>
            <li>Comparativo del aliado BRM en los últimos 3 meses</li>
            <li>Comparativo del producto Internet en los últimos 3 meses</li>
            <li>¿Cuál fue mi mejor mes en ventas a lo largo del año?</li>
        </ul>
        '''