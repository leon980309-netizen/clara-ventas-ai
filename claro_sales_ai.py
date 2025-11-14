import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import re
import json
import os

from groq import Groq

# Inicializa cliente de Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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
        self.sales_df = self.load_csv_from_url(url_consolidado)
        self.metas_df = self.load_csv_from_url(url_metas)
        print(f"✅ Datos cargados: {len(self.sales_df)} filas en ventas")

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

    # === LÓGICA ANALÍTICA ===
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

    def get_comparativo_dos_aliados_3meses(self, aliado1, aliado2):
        meses = self.get_last_n_months(3)
        df = self.sales_df.copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        df_filtrado = df[(df['ALIADO'].isin([aliado1, aliado2])) & (df['Mes_Año'].isin(meses))]
        if df_filtrado.empty: return None
        comparativo = df_filtrado.groupby(['Mes_Año', 'ALIADO']).agg({'ALTAS': 'sum', 'INGRESOS': 'sum'}).reset_index()
        pivot_altas = comparativo.pivot(index='Mes_Año', columns='ALIADO', values='ALTAS').fillna(0)
        pivot_ingresos = comparativo.pivot(index='Mes_Año', columns='ALIADO', values='INGRESOS').fillna(0)
        for aliado in [aliado1, aliado2]:
            if aliado not in pivot_altas.columns: pivot_altas[aliado] = 0
            if aliado not in pivot_ingresos.columns: pivot_ingresos[aliado] = 0
        pivot_altas = pivot_altas.reindex(meses, fill_value=0)
        pivot_ingresos = pivot_ingresos.reindex(meses, fill_value=0)
        return {'meses': meses, 'altas': pivot_altas[[aliado1, aliado2]].to_dict(), 'ingresos': pivot_ingresos[[aliado1, aliado2]].to_dict()}

    def get_proyeccion_aliados(self, mes=None):
        if mes is None: mes = self.get_current_month()
        year, month = map(int, mes.split('-'))
        primer_dia = datetime(year, month, 1)
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if hoy.month != month or hoy.year != year: return None
        ultimo_dia = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        dias_trans = self.contar_dias_habiles(primer_dia, min(hoy, ultimo_dia))
        dias_tot = self.contar_dias_habiles(primer_dia, ultimo_dia)
        if dias_trans == 0 or dias_tot == 0: return None

        df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
        df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        ventas = df.groupby('ALIADO').agg({'ALTAS':'sum','INGRESOS':'sum'}).reset_index()

        metas = self.metas_df.copy()
        metas['MES'] = pd.to_datetime(metas['MES'], format='%d/%m/%Y', errors='coerce')
        metas = metas.dropna(subset=['MES'])
        metas['Mes_Año'] = metas['MES'].dt.strftime('%Y-%m')
        metas = metas[metas['Mes_Año'] == mes]
        metas['ALIADO'] = metas['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
        metas['Ingresos'] = pd.to_numeric(
            metas['Ingresos'].astype(str)
            .str.replace(r'[$\s.]', '', regex=True)
            .replace('-', '0'),
            errors='coerce'
        ).fillna(0)
        metas_agg = metas.groupby('ALIADO').agg({'Altas':'sum','Ingresos':'sum'}).reset_index()

        proj = pd.merge(ventas, metas_agg, on='ALIADO', how='outer').fillna(0)
        proj['PROY_ALTAS'] = (proj['ALTAS'] / dias_trans) * dias_tot
        proj['PROY_INGRESOS'] = (proj['INGRESOS'] / dias_trans) * dias_tot
        proj['PROY_ALTAS_%'] = (proj['PROY_ALTAS'] / proj['Altas'].replace(0, 1)) * 100
        proj['PROY_INGRESOS_%'] = (proj['PROY_INGRESOS'] / proj['Ingresos'].replace(0, 1)) * 100
        proj = proj.replace([float('inf'), -float('inf')], 0)
        return proj.to_dict(orient='records'), dias_trans, dias_tot

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

    # === INTERPRETACIÓN CON GROQ (MODELO ACTUALIZADO) ===
    def interpretar_pregunta(self, pregunta):
        prompt = f"""
Eres un asistente analítico de ventas. Convierte la pregunta en JSON con:
- intencion: "cumplimiento", "desempeño", "producto_mas_vendido", "aliado_top_producto", 
  "comparativo_dos_aliados", "proyeccion", "grafico_producto_aliado"
- aliado: nombre en mayúsculas (ATENTO, COS, etc.) o null
- aliado2: segundo aliado o null
- producto: en minúsculas (adicionales, internet, etc.) o null
- periodo: "mes_actual", "ultimos_3_meses", "anio", o "2025-10"

Solo responde con el JSON.

Pregunta: "{pregunta}"
"""
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",  # ✅ MODELO ACTUAL Y SOPORTADO
                temperature=0.1,
                max_tokens=150
            )
            json_str = chat_completion.choices[0].message.content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0]
            return json.loads(json_str)
        except Exception as e:
            print(f"❌ Error en Groq: {e}")
            return {"intencion": "desconocida"}

    def ask(self, question):
        intent = self.interpretar_pregunta(question)
        intencion = intent.get("intencion")
        aliado = intent.get("aliado")
        aliado2 = intent.get("aliado2")
        producto = intent.get("producto")
        periodo = intent.get("periodo", "mes_actual")

        mes = self.get_current_month() if periodo in ["mes_actual", "ultimos_3_meses", "anio"] else periodo

        try:
            if intencion == "grafico_producto_aliado" and aliado:
                df = self.sales_df[self.sales_df['Mes_Año'] == mes].copy()
                df['ALIADO'] = df['CAMPAÑA FINAL'].map(self.homologacion_aliados).fillna('DESCONOCIDO')
                df_f = df[df['ALIADO'] == aliado]
                if df_f.empty:
                    return f"<p>❌ No hay datos para <strong>{aliado}</strong> en {mes}.</p>"
                resumen = df_f.groupby('BASE').agg({'ALTAS': 'sum', 'INGRESOS': 'sum'}).reset_index().sort_values('ALTAS', ascending=False)
                if resumen.empty:
                    return f"<p>❌ No hay productos con ventas para <strong>{aliado}</strong>.</p>"
                productos = resumen['BASE'].tolist()
                altas = resumen['ALTAS'].astype(int).tolist()
                ingresos = resumen['INGRESOS'].astype(float).tolist()
                chart_id = f"chart_{aliado.lower()}"
                chart_html = f'''
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
                return chart_html

            elif intencion == "aliado_top_producto" and producto:
                res = self.get_top_aliado_por_producto(producto, mes)
                if res:
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">🏆 Aliado con más ventas de '{producto.title()}' en {res['mes']}</h3>
                        <p><strong>Aliado:</strong> {res['aliado']}</p>
                        <p><strong>Altas:</strong> {res['altas']:,}</p>
                        <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                    </div>
                    '''
            elif intencion == "producto_mas_vendido":
                res = self.get_producto_mas_vendido('3meses' if periodo == "ultimos_3_meses" else 'mes')
                if res:
                    txt = "en los últimos 3 meses" if periodo == "ultimos_3_meses" else f"en {mes}"
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">🔥 Producto más vendido {txt}</h3>
                        <p><strong>Producto:</strong> {res['producto']}</p>
                        <p><strong>Altas:</strong> {res['altas']:,}</p>
                        <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                    </div>
                    '''
            elif intencion == "comparativo_dos_aliados" and aliado and aliado2:
                datos = self.get_comparativo_dos_aliados_3meses(aliado, aliado2)
                if datos:
                    headers = ['Mes', f'{aliado} - Altas', f'{aliado2} - Altas', f'{aliado} - Ingresos', f'{aliado2} - Ingresos']
                    rows = []
                    for m in datos['meses']:
                        a1a = int(datos['altas'][aliado].get(m, 0))
                        a2a = int(datos['altas'][aliado2].get(m, 0))
                        a1i = float(datos['ingresos'][aliado].get(m, 0))
                        a2i = float(datos['ingresos'][aliado2].get(m, 0))
                        rows.append([m, f"{a1a:,}", f"{a2a:,}", f"${a1i:,.0f}", f"${a2i:,.0f}"])
                    tabla = self._generate_html_table(headers, rows)
                    total1a = sum(datos['altas'][aliado].values())
                    total2a = sum(datos['altas'][aliado2].values())
                    total1i = sum(datos['ingresos'][aliado].values())
                    total2i = sum(datos['ingresos'][aliado2].values())
                    lider_altas = aliado if total1a > total2a else aliado2
                    lider_ing = aliado if total1i > total2i else aliado2
                    return f"<h3 style='color:#e60000;'>📊 Comparativo: {aliado} vs {aliado2}</h3>{tabla}<p><strong>🔍 Análisis:</strong> {lider_altas} lidera en altas, {lider_ing} en ingresos.</p>"
            elif intencion == "cumplimiento" and aliado:
                cumplimiento = self.get_cumplimiento_detalle(aliado=aliado, producto=producto, mes=mes)
                if cumplimiento:
                    if producto:
                        item = cumplimiento[0]
                        return f'''
                        <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                            <h3 style="color:#e60000;">🎯 Cumplimiento de {aliado} en {producto.title()} ({mes})</h3>
                            <p><strong>Altas:</strong> {int(item['ALTAS_REALES']):,} / {int(item['META_ALTAS']):,} → <strong>{item['CUMPLIMIENTO_ALTAS_%']}%</strong></p>
                            <p><strong>Ingresos:</strong> ${float(item['INGRESOS_REALES']):,.0f} / ${float(item['META_INGRESOS']):,.0f} → <strong>{item['CUMPLIMIENTO_INGRESOS_%']}%</strong></p>
                        </div>
                        '''
                    else:
                        headers = ['Producto', 'Altas Reales', 'Meta Altas', 'Cumpl. Altas (%)', 'Ingresos Reales', 'Meta Ingresos', 'Cumpl. Ingresos (%)']
                        rows = [[item['BASE'], f"{int(item['ALTAS_REALES']):,}", f"{int(item['META_ALTAS']):,}", f"{item['CUMPLIMIENTO_ALTAS_%']}%", f"${float(item['INGRESOS_REALES']):,.0f}", f"${float(item['META_INGRESOS']):,.0f}", f"{item['CUMPLIMIENTO_INGRESOS_%']}%"] for item in cumplimiento]
                        tabla = self._generate_html_table(headers, rows)
                        return f"<h3 style='color:#e60000;'>🎯 Cumplimiento de {aliado} por producto ({mes})</h3>{tabla}"
            elif intencion == "desempeño" and aliado:
                res = self.get_desempeno_aliado(aliado, mes)
                if res:
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">📊 {res['aliado']} en {res['mes']}</h3>
                        <p><strong>Altas:</strong> {res['altas']:,}</p>
                        <p><strong>Ingresos:</strong> ${res['ingresos']:,.0f}</p>
                    </div>
                    '''
            elif intencion == "proyeccion":
                resultado = self.get_proyeccion_aliados(mes)
                if resultado:
                    datos, dt, dtt = resultado
                    headers = ['Aliado', 'Proy. Altas (%)', 'Proy. Ingresos (%)']
                    rows = [[d['ALIADO'], f"{d['PROY_ALTAS_%']:.1f}%", f"{d['PROY_INGRESOS_%']:.1f}%"] for d in datos]
                    tabla = self._generate_html_table(headers, rows)
                    return f'''
                    <div style="background:#f9f9f9; padding:15px; border-radius:8px; margin:10px 0;">
                        <h3 style="color:#e60000;">📈 Proyección de cumplimiento - {mes}</h3>
                        <p><strong>Días hábiles transcurridos:</strong> {dt} de {dtt}</p>
                        <p><em>Proyección = (Ventas actuales / Días transcurridos) × Días totales del mes</em></p>
                    </div>
                    {tabla}
                    '''
        except Exception as e:
            return f"<p>❌ Error en análisis: {str(e)}</p>"

        return '''
        <p>🤖 Puedes preguntarme:</p>
        <ul style="padding-left:20px; margin:10px 0;">
            <li>¿Cumplimiento del aliado ATENTO?</li>
            <li>¿Qué aliado vendió más Adicionales este mes?</li>
            <li>¿Cuál es el producto más vendido en los últimos 3 meses?</li>
            <li>Comparativo: COS vs BRM en los últimos 3 meses</li>
            <li>Dame la proyección de cumplimiento este mes</li>
            <li>Haz un graficado de comportamiento por producto de aliado COS</li>
        </ul>
        '''