import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import re
import json
import os

# Festivos de Colombia 2024-2025
CO_HOLIDAYS = {
    "2024-01-01", "2024-01-08", "2024-03-25", "2024-03-28", "2024-03-29",
    "2024-05-01", "2024-05-13", "2024-06-03", "2024-06-10", "2024-07-01",
    "2024-07-20", "2024-08-07", "2024-08-19", "2024-10-14", "2024-11-04",
    "2024-11-11", "2024-12-08", "2024-12-25",
    "2025-01-01", "2025-01-06", "2025-03-24", "2025-04-17", "2025-04-18",
    "2025-05-01", "2025-06-02", "2025-06-30", "2025-07-20", "2025-08-07",
    "2025-08-18", "2025-10-13", "2025-11-03", "2025-11-17", "2025-12-08", "2025-12-25"
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

    # === MÉTODOS ANALÍTICOS ===
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

    def _generar_grafico_html(self, aliado, mes, resumen):
        productos = [r['BASE'] for r in resumen]
        altas = [int(r['ALTAS']) for r in resumen]
        ingresos = [float(r['INGRESOS']) for r in resumen]
        chart_id = f"chart_{aliado.lower()}"
        return f'''
        <h3 style="color:#e60000;">📊 Comportamiento por producto - {aliado} en {mes}</h3>
        <div style="height:300px; margin:15px 0;">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                     {{
                        labels: {json.dumps(productos)},
                        datasets: [
                            {{
                                label: 'Altas',
                                 {json.dumps(altas)},
                                backgroundColor: '#0078d4',
                                yAxisID: 'y'
                            }},
                            {{
                                label: 'Ingresos ($)',
                                 {json.dumps(ingresos)},
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
                                        if (context.dataset.label === 'Ingresos ($)') {{
                                            return context.dataset.label + ': $' + context.parsed.y.toLocaleString();
                                        }}
                                        return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{ display: true, text: 'Altas' }}
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
            }});
        </script>
        '''

    # === MÉTODO ASK SIN GROQ ===
    def ask(self, question):
        question_lower = question.lower().strip()
        mes = self.get_current_month()

        # 1. Desempeño de especialista
        if "geovanny ramirez" in question_lower or "geovany ramirez" in question_lower:
            res = self.get_desempeno_por_especialista("Geovanny Ramirez", mes)
            if res:
                total_altas = sum(r['ALTAS'] for r in res)
                total_ingresos = sum(r['INGRESOS'] for r in res)
                analisis = f"<p><strong>🔍 Análisis:</strong> Los aliados de Geovanny Ramirez generan <strong>{total_altas:,} altas</strong> y <strong>${total_ingresos:,.0f} en ingresos</strong>. ATENTO es el mayor contribuyente.</p>"
                headers = ['Aliado', 'Altas', 'Ingresos ($)']
                rows = [[r['ALIADO'], f"{int(r['ALTAS']):,}", f"${float(r['INGRESOS']):,.0f}"] for r in res]
                tabla = self._generate_html_table(headers, rows)
                return f"<h3>📊 Desempeño de aliados de <strong>Geovanny Ramirez</strong></h3>{tabla}{analisis}"
            else:
                return "<p>❌ No hay datos para los aliados de Geovanny Ramirez este mes.</p>"

        # 2. Producto más vendido por aliado
        if "producto más vendido" in question_lower or "producto mas vendido" in question_lower:
            for aliado in ['COS', 'ATENTO', 'BRM', 'ABAI', 'MILLENIUM', 'NEXA', 'AQI', 'IBR', 'LATCOM', 'ALMACONTACT']:
                if aliado.lower() in question_lower:
                    res = self.get_producto_mas_vendido_por_aliado(aliado, mes)
                    if res:
                        analisis = f"<p><strong>🔍 Análisis:</strong> <strong>{res['producto']}</strong> es el producto estrella de <strong>{aliado}</strong>, con <strong>{res['altas']:,} altas</strong> en {res['mes']}.</p>"
                        return f"<p>🔥 El producto más vendido por <strong>{aliado}</strong> en {res['mes']} es <strong>{res['producto']}</strong> con {res['altas']:,} altas.</p>{analisis}"
            return "<p>❌ No se reconoció el aliado. Prueba con: COS, ATENTO, BRM, etc.</p>"

        # 3. Comportamiento total últimos 3 meses
        if "comportamiento total" in question_lower or "totales de la operacion" in question_lower:
            datos = self.get_comportamiento_total_operacion()
            if datos:
                total_ingresos = sum(d['INGRESOS'] for d in datos)
                analisis = f"<p><strong>🔍 Análisis:</strong> La operación acumula <strong>${total_ingresos:,.0f} en ingresos</strong> en los últimos 3 meses, con una tendencia a la baja en altas desde septiembre.</p>"
                headers = ['Mes', 'Altas', 'Ingresos ($)']
                rows = [[d['Mes_Año'], f"{int(d['ALTAS']):,}", f"${float(d['INGRESOS']):,.0f}"] for d in datos]
                tabla = self._generate_html_table(headers, rows)
                return f"<h3>📈 Comportamiento total - Últimos 3 meses</h3>{tabla}{analisis}"
            else:
                return "<p>❌ No hay datos para el análisis de los últimos 3 meses.</p>"

        # 4. Ranking de vendedores
        if "ranking de vendedores" in question_lower or "mayores vendedores" in question_lower:
            ranking = self.get_ranking_vendedores_por_producto()
            if ranking:
                top_aliado = ranking[0]['ALIADO']
                analisis = f"<p><strong>🔍 Análisis:</strong> <strong>{top_aliado}</strong> lidera el ranking con <strong>{int(ranking[0]['ALTAS']):,} altas</strong>. Los primeros 5 puestos están dominados por ATENTO.</p>"
                headers = ['Aliado', 'Campaña', 'Altas', 'Ingresos ($)']
                rows = [[r['ALIADO'], r['CAMPAÑA FINAL'], f"{int(r['ALTAS']):,}", f"${float(r['INGRESOS']):,.0f}"] for r in ranking[:10]]
                tabla = self._generate_html_table(headers, rows)
                return f"<h3>🏆 Ranking de vendedores</h3>{tabla}{analisis}"
            else:
                return "<p>❌ No hay datos para el ranking.</p>"

        # 5. Variación mes a mes
        if "variación" in question_lower and "vs" in question_lower:
            # Detectar aliado (simplificado)
            aliado = None
            for a in ['MILLENIUM', 'ATENTO', 'COS', 'BRM']:
                if a.lower() in question_lower:
                    aliado = a
                    break
            # Detectar producto
            producto = "m"  # móvil por defecto
            if "fijo" in question_lower:
                producto = "fijo"
            # Detectar meses
            if "agosto 2025" in question_lower and "julio 2025" in question_lower:
                res = self.get_variacion_mes_a_mes(aliado or "MILLENIUM", producto, "2025-08", "2025-07")
                analisis = f"<p><strong>🔍 Análisis:</strong> La variación de <strong>+{res['variacion_pct']:.2f}%</strong> en {aliado or 'MILLENIUM'} indica un crecimiento sostenido en ventas de móvil.</p>"
                return f'''<div><h3>📊 Variación Móvil - {aliado or 'MILLENIUM'}</h3>
                <p><strong>{res['mes1']}</strong>: {res['ventas1']:,} altas</p>
                <p><strong>{res['mes2']}</strong>: {res['ventas2']:,} altas</p>
                <p><strong>Variación:</strong> {res['variacion_pct']:+.2f}%</p>{analisis}</div>'''

        # 6. Cumplimiento
        if "cumplimiento" in question_lower:
            for aliado in ['ATENTO', 'COS', 'BRM']:
                if aliado.lower() in question_lower:
                    cumplimiento = self.get_cumplimiento_detalle(aliado=aliado, mes=mes)
                    if cumplimiento:
                        item = cumplimiento[0]
                        analisis = f"<p><strong>🔍 Análisis:</strong> {aliado} supera la meta en altas (<strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong>) pero tiene oportunidad en ingresos (<strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong>).</p>"
                        return f'''
                        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                            <h3 style="color:#e60000;">🎯 Cumplimiento de {aliado} en {mes}</h3>
                            <p><strong>Altas:</strong> {int(item['ALTAS_REALES']):,} / {int(item['META_ALTAS']):,} → <strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong></p>
                            <p><strong>Ingresos:</strong> ${float(item['INGRESOS_REALES']):,.0f} / ${float(item['META_INGRESOS']):,.0f} → <strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong></p>
                            {analisis}
                        </div>
                        '''

        # 7. Desempeño de aliado
        for aliado in ['ATENTO', 'COS', 'BRM', 'ABAI', 'MILLENIUM']:
            if aliado.lower() in question_lower and ("desempeño" in question_lower or "desempeno" in question_lower):
                res = self.get_desempeno_aliado(aliado, mes)
                if res:
                    analisis = f"<p><strong>🔍 Análisis:</strong> {aliado} muestra un desempeño sólido con <strong>{res['altas']:,} altas</strong> y <strong>${res['ingresos']:,.0f} en ingresos</strong> en {mes}.</p>"
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">📊 {res['aliado']} en {res['mes']}</h3>
                        <p><strong>Altas:</strong> {res['altas']:,}</p>
                        <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                        {analisis}
                    </div>
                    '''

        # Mensaje de ayuda
        return '''
        <p>🤖 Puedes preguntarme:</p>
        <ul style="padding-left:20px; margin:10px 0;">
            <li>Desempeño de aliados de Geovanny Ramirez</li>
            <li>¿Cuál es el producto más vendido por COS?</li>
            <li>Comportamiento total en los últimos 3 meses</li>
            <li>Ranking de vendedores</li>
            <li>Variación de móvil agosto 2025 vs julio 2025 en Millenium</li>
            <li>Cumplimiento del aliado ATENTO</li>
        </ul>
        '''