import pandas as pd
import re
from campaign_mapping import get_campañas_por_aliado

class AnalysisEngine:
    def __init__(self, df_consolidado, df_metas):
        self.df = df_consolidado
        self.df_metas = df_metas
        # ELIMINADO sentence-transformers para ahorrar memoria

        self.intents = {
            'desempeño': ['desempeño', 'rendimiento', 'eficiencia', 'cómo le fue', 'resultado', 'desempeno', 'ventas', 'altas'],
            'predicción': ['predicción', 'cumplirá', 'va a cumplir', 'cerca de la meta', 'lejos de la meta', 'pronóstico', 'proyección', 'cumplimiento'],
            'comparación': ['versus', 'comparar', 'diferencia', 'mejor periodo', 'vs', 'comparación', 'comparativo'],
            'generar power bi': ['power bi', 'archivo para power bi', 'exportar a power bi', 'visualización', 'dashboard']
        }

        self.aliados_validos = [
            "ABAI", "ALMACONTACT", "AQI", "ATENTO", "BRM", "CLARO",
            "COS", "IBR LATAM", "LATCOM", "MILLENIUM", "NEXA"
        ]

        # Mapeo de meses en español a números
        self.meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }

    def filtrar_por_aliado(self, df, aliado=None):
        if aliado is None:
            return df
        campañas = get_campañas_por_aliado(aliado)
        if not campañas:
            return df[df['campana_final'] == aliado.upper()]
        return df[df['campana_final'].isin(campañas)]

    def detect_intent(self, pregunta):
        """Detección simple por palabras clave - SIN machine learning"""
        pregunta_lower = pregunta.lower()
        
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in pregunta_lower:
                    return intent
                    
        return "desconocido"

    def detectar_aliado_en_pregunta(self, pregunta):
        pregunta_upper = pregunta.upper()
        for aliado in self.aliados_validos:
            if aliado in pregunta_upper:
                return aliado
        return None

    def detectar_periodo(self, pregunta):
        pregunta_lower = pregunta.lower()
        
        for mes_nombre, mes_num in self.meses.items():
            if mes_nombre in pregunta_lower:
                def filtro(df):
                    return df[
                        df['mes'].astype(str).str.contains(f"2025.*{mes_num}", case=False, na=False) |
                        df['mes'].astype(str).str.contains(f"{mes_num}.*2025", case=False, na=False)
                    ]
                return filtro
        return None

    def responder(self, pregunta, user_info):
        intent = self.detect_intent(pregunta)
        
        aliado = None
        if user_info["role"] == "admin":
            aliado = self.detectar_aliado_en_pregunta(pregunta)
        else:
            aliado = user_info["base"]

        if intent == "desempeño":
            return self.analizar_desempenio(aliado, pregunta)
        elif intent == "predicción":
            return self.predecir_cumplimiento(aliado, pregunta)
        elif intent == "comparación":
            return self.comparar_periodos(aliado, pregunta)
        elif intent == "generar power bi":
            return "📊 El dashboard ya está visible en el panel izquierdo. ¿En qué más puedo ayudarte?"
        else:
            return "🤖 No entendí tu pregunta. Puedo ayudarte con:\n• 📊 Desempeño\n• 🎯 Predicción\n• 📈 Comparaciones\n\nEjemplo: '¿Cómo le fue a CLARO en enero?'"

    def analizar_desempenio(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
        
        if df.empty:
            return f"❌ No se encontraron datos para {aliado if aliado else 'el periodo seleccionado'}"
        
        total_altas = df['altas'].sum()
        total_ingresos = df['ingresos'].sum()

        if aliado:
            return f"📊 **{aliado}**:\n• Altas: {total_altas:,.0f}\n• Ingresos: S/ {total_ingresos:,.2f}"
        else:
            return f"📊 **Global**:\n• Altas: {total_altas:,.0f}\n• Ingresos: S/ {total_ingresos:,.2f}"

    def predecir_cumplimiento(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        df_metas = self.filtrar_por_aliado(self.df_metas, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
            df_metas = filtro_periodo(df_metas)
        
        if df.empty or df_metas.empty:
            return f"❌ No se encontraron datos o metas para {aliado}"
        
        altas_logradas = df['altas'].sum()
        meta_altas = df_metas['altas'].sum() if 'altas' in df_metas.columns else 0
        
        if meta_altas == 0:
            return "❌ No hay metas definidas"
        
        cumplimiento = (altas_logradas / meta_altas * 100)
        estado = "✅ Sí" if cumplimiento >= 80 else "⚠️ Parcialmente" if cumplimiento >= 50 else "❌ No"
        
        return f"🎯 **{aliado}**:\n• Cumplimiento: {cumplimiento:.1f}%\n• Estado: {estado}"

    def comparar_periodos(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        
        # Comparar primeros meses disponibles de 2025
        meses = ['01', '02', '03']
        resultados = {}
        
        for mes in meses:
            df_mes = df[df['mes'].astype(str).str.contains(f"2025.*{mes}", na=False)]
            if not df_mes.empty:
                resultados[mes] = df_mes['altas'].sum()
        
        if len(resultados) < 2:
            return "❌ No hay suficientes datos para comparar"
        
        mejor_mes = max(resultados, key=resultados.get)
        
        respuesta = f"🆚 **Comparación {aliado}**:\n"
        for mes, altas in resultados.items():
            respuesta += f"• Mes {mes}: {altas:,.0f} altas\n"
        respuesta += f"• Mejor: Mes {mejor_mes}"
        
        return respuesta