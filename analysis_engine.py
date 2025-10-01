from sentence_transformers import SentenceTransformer, util
import pandas as pd
import re
from campaign_mapping import get_campañas_por_aliado

class AnalysisEngine:
    def __init__(self, df_consolidado, df_metas):
        self.df = df_consolidado
        self.df_metas = df_metas
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

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
        pregunta_emb = self.model.encode(pregunta.lower(), convert_to_tensor=True)
        best_intent = None
        best_score = 0.0
        for intent, keywords in self.intents.items():
            for kw in keywords:
                kw_emb = self.model.encode(kw, convert_to_tensor=True)
                sim = util.cos_sim(pregunta_emb, kw_emb).item()
                if sim > best_score:
                    best_score = sim
                    best_intent = intent
        return best_intent if best_score > 0.3 else "desconocido"

    def detectar_aliado_en_pregunta(self, pregunta):
        pregunta_upper = pregunta.upper()
        for aliado in self.aliados_validos:
            if aliado in pregunta_upper:
                return aliado
        return None

    def detectar_periodo(self, pregunta):
        """Detección optimizada para 2025"""
        pregunta_lower = pregunta.lower()
        
        # Detectar mes específico
        mes_num = None
        mes_nombre_detectado = None
        for mes_nombre, num in self.meses.items():
            if mes_nombre in pregunta_lower:
                mes_num = num
                mes_nombre_detectado = mes_nombre
                break
        
        def filtro(df):
            if mes_num:
                # Buscar en datos de 2025 con el mes detectado
                return df[
                    df['mes'].astype(str).str.contains(f"2025.*{mes_num}", case=False, na=False) |
                    df['mes'].astype(str).str.contains(f"{mes_num}.*2025", case=False, na=False) |
                    df['mes'].astype(str).str.contains(mes_nombre_detectado, case=False, na=False)
                ]
            return df
        
        return filtro

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
            return "🤖 No entendí tu pregunta. Puedo ayudarte con:\n• Desempeño de aliados\n• Predicción de cumplimiento\n• Comparaciones entre periodos\n• Consultas sobre ventas y altas"

    def analizar_desempenio(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
        
        if df.empty:
            periodo_msg = self._construir_mensaje_periodo(pregunta)
            return f"❌ No se encontraron datos para {aliado if aliado else 'el aliado'}{periodo_msg}"
        
        total_altas = df['altas'].sum()
        total_ingresos = df['ingresos'].sum()
        
        periodo_msg = self._construir_mensaje_periodo(pregunta)

        if aliado:
            return (
                f"📊 **Desempeño de {aliado}**{periodo_msg}:\n\n"
                f"• **Altas totales:** {total_altas:,.0f}\n"
                f"• **Ingresos totales:** S/ {total_ingresos:,.2f}\n"
                f"• **Registros analizados:** {len(df):,}"
            )
        else:
            return (
                f"📊 **Desempeño Global**{periodo_msg}:\n\n"
                f"• **Altas totales:** {total_altas:,.0f}\n"
                f"• **Ingresos totales:** S/ {total_ingresos:,.2f}\n"
                f"• **Registros analizados:** {len(df):,}"
            )

    def predecir_cumplimiento(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        df_metas = self.filtrar_por_aliado(self.df_metas, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
            df_metas = filtro_periodo(df_metas)
        
        if df.empty or df_metas.empty:
            periodo_msg = self._construir_mensaje_periodo(pregunta)
            return f"❌ No se encontraron datos o metas para {aliado if aliado else 'el aliado'}{periodo_msg}"
        
        altas_logradas = df['altas'].sum()
        ingresos_logrados = df['ingresos'].sum()
        meta_altas = df_metas['altas'].sum() if 'altas' in df_metas.columns else 0
        meta_ingresos = df_metas['ingresos'].sum() if 'ingresos' in df_metas.columns else 0
        
        if meta_altas == 0 or meta_ingresos == 0:
            return "❌ No se encontraron metas definidas para el análisis."
        
        cumplimiento_altas = (altas_logradas / meta_altas * 100) if meta_altas > 0 else 0
        cumplimiento_ingresos = (ingresos_logrados / meta_ingresos * 100) if meta_ingresos > 0 else 0
        
        # Estados más detallados
        if cumplimiento_altas >= 90:
            estado_altas = "🟢 Excelente - Supera meta"
        elif cumplimiento_altas >= 80:
            estado_altas = "🟢 Bueno - Cerca de meta"
        elif cumplimiento_altas >= 60:
            estado_altas = "🟡 Regular - En progreso"
        else:
            estado_altas = "🔴 Crítico - Lejos de meta"
            
        if cumplimiento_ingresos >= 90:
            estado_ingresos = "🟢 Excelente - Supera meta"
        elif cumplimiento_ingresos >= 80:
            estado_ingresos = "🟢 Bueno - Cerca de meta"
        elif cumplimiento_ingresos >= 60:
            estado_ingresos = "🟡 Regular - En progreso"
        else:
            estado_ingresos = "🔴 Crítico - Lejos de meta"
        
        periodo_msg = self._construir_mensaje_periodo(pregunta)

        if aliado:
            return (
                f"🎯 **Predicción de Cumplimiento - {aliado}**{periodo_msg}:\n\n"
                f"**ALTAS:**\n"
                f"• Logrado: {altas_logradas:,.0f} / Meta: {meta_altas:,.0f}\n"
                f"• Cumplimiento: {cumplimiento_altas:.1f}% → {estado_altas}\n\n"
                f"**INGRESOS:**\n"
                f"• Logrado: S/ {ingresos_logrados:,.2f} / Meta: S/ {meta_ingresos:,.2f}\n"
                f"• Cumplimiento: {cumplimiento_ingresos:.1f}% → {estado_ingresos}"
            )
        else:
            return (
                f"🎯 **Predicción de Cumplimiento Global**{periodo_msg}:\n\n"
                f"**ALTAS:**\n"
                f"• Logrado: {altas_logradas:,.0f} / Meta: {meta_altas:,.0f}\n"
                f"• Cumplimiento: {cumplimiento_altas:.1f}% → {estado_altas}\n\n"
                f"**INGRESOS:**\n"
                f"• Logrado: S/ {ingresos_logrados:,.2f} / Meta: S/ {meta_ingresos:,.2f}\n"
                f"• Cumplimiento: {cumplimiento_ingresos:.1f}% → {estado_ingresos}"
            )

    def comparar_periodos(self, aliado, pregunta):
        """Comparación optimizada para datos de 2025"""
        df = self.filtrar_por_aliado(self.df, aliado)
        
        if df.empty:
            return f"❌ No se encontraron datos para {aliado if aliado else 'análisis'}."
        
        # Comparar diferentes meses dentro de 2025
        meses_comparacion = {}
        for mes_nombre, mes_num in list(self.meses.items())[:3]:  # Solo primeros 3 meses para ejemplo
            df_mes = df[
                df['mes'].astype(str).str.contains(f"2025.*{mes_num}", case=False, na=False) |
                df['mes'].astype(str).str.contains(mes_nombre, case=False, na=False)
            ]
            if not df_mes.empty:
                meses_comparacion[mes_nombre.capitalize()] = {
                    'altas': df_mes['altas'].sum(),
                    'ingresos': df_mes['ingresos'].sum()
                }
        
        if len(meses_comparacion) < 2:
            return "❌ No hay suficientes datos de diferentes periodos para comparar."
        
        # Encontrar mejor mes
        mejor_mes_altas = max(meses_comparacion.items(), key=lambda x: x[1]['altas'])
        mejor_mes_ingresos = max(meses_comparacion.items(), key=lambda x: x[1]['ingresos'])
        
        if aliado:
            respuesta = f"🆚 **Comparación de Periodos - {aliado} (2025)**:\n\n"
        else:
            respuesta = f"🆚 **Comparación de Periodos Global (2025)**:\n\n"
        
        for mes, datos in meses_comparacion.items():
            respuesta += f"**{mes}:**\n"
            respuesta += f"• Altas: {datos['altas']:,.0f}\n"
            respuesta += f"• Ingresos: S/ {datos['ingresos']:,.2f}\n\n"
        
        respuesta += f"**RESUMEN:**\n"
        respuesta += f"• Mejor en altas: {mejor_mes_altas[0]} ({mejor_mes_altas[1]['altas']:,.0f})\n"
        respuesta += f"• Mejor en ingresos: {mejor_mes_ingresos[0]} (S/ {mejor_mes_ingresos[1]['ingresos']:,.2f})"
        
        return respuesta

    def _construir_mensaje_periodo(self, pregunta):
        """Construye mensaje descriptivo del periodo"""
        pregunta_lower = pregunta.lower()
        
        for mes_nombre in self.meses.keys():
            if mes_nombre in pregunta_lower:
                return f" en {mes_nombre.capitalize()} 2025"
        
        # Si no se detecta mes específico, asumir todo 2025
        if '2024' in pregunta:
            return " en 2024 (datos limitados)"
        else:
            return " en 2025"

    def obtener_estadisticas_rapidas(self, aliado=None):
        """Método auxiliar para estadísticas rápidas"""
        df = self.filtrar_por_aliado(self.df, aliado)
        
        if df.empty:
            return "No hay datos disponibles."
        
        total_altas = df['altas'].sum()
        total_ingresos = df['ingresos'].sum()
        aliados_unicos = df['campana_final'].nunique()
        
        return f"📈 Stats: {total_altas:,.0f} altas, S/ {total_ingresos:,.2f} ingresos, {aliados_unicos} aliados"