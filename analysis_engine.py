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
            'desempeño': ['desempeño', 'rendimiento', 'eficiencia', 'cómo le fue', 'resultado', 'desempeno'],
            'predicción': ['predicción', 'cumplirá', 'va a cumplir', 'cerca de la meta', 'lejos de la meta', 'pronóstico', 'proyección'],
            'comparación': ['versus', 'comparar', 'diferencia', 'mejor periodo', 'vs', 'comparación'],
            'generar power bi': ['power bi', 'archivo para power bi', 'exportar a power bi', 'visualización']
        }

        self.aliados_validos = [
            "ABAI", "ALMACONTACT", "AQI", "ATENTO", "BRM", "CLARO",
            "COS", "IBR LATAM", "LATCOM", "MILLENIUM", "NEXA"
        ]

        # Mapeo de meses en español a números
        self.meses = {
            'enero': '1', 'febrero': '2', 'marzo': '3', 'abril': '4',
            'mayo': '5', 'junio': '6', 'julio': '7', 'agosto': '8',
            'septiembre': '9', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
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
        """Mejorada para detectar año y mes específicos"""
        pregunta_lower = pregunta.lower()
        
        # Detectar año específico
        año = None
        for year in ['2024', '2025']:
            if year in pregunta:
                año = year
                break
        
        # Detectar mes
        mes_num = None
        for mes_nombre, num in self.meses.items():
            if mes_nombre in pregunta_lower:
                mes_num = num
                break
        
        def filtro(df):
            if año and mes_num:
                # Buscar patrones como "2024-09", "09/2024", "Septiembre 2024"
                return df[
                    df['mes'].astype(str).str.contains(f"{año}.*{mes_num}", case=False, na=False) |
                    df['mes'].astype(str).str.contains(f"{mes_num}.*{año}", case=False, na=False)
                ]
            elif año:
                return df[df['mes'].astype(str).str.contains(año, case=False, na=False)]
            elif mes_num:
                # Asumir año actual (2025) si no se especifica
                return df[df['mes'].astype(str).str.contains(f"2025.*{mes_num}", case=False, na=False)]
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
            return "Lo siento, no entendí. Puedo ayudarte con desempeño, predicción, comparación."

    def analizar_desempenio(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
        
        if df.empty:
            return "❌ No se encontraron datos para el periodo o aliado especificado."
        
        total_altas = df['altas'].sum()
        total_ingresos = df['ingresos'].sum()
        
        # Construir mensaje de periodo
        periodo_msg = self._construir_mensaje_periodo(pregunta)

        if aliado:
            return f"📊 Desempeño del aliado **{aliado}**{periodo_msg}:\n- Altas totales: {total_altas:,.0f}\n- Ingresos totales: S/ {total_ingresos:,.2f}"
        else:
            return f"📊 Desempeño global{periodo_msg}:\n- Altas totales: {total_altas:,.0f}\n- Ingresos totales: S/ {total_ingresos:,.2f}"

    def predecir_cumplimiento(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        df_metas = self.filtrar_por_aliado(self.df_metas, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
            df_metas = filtro_periodo(df_metas)
        
        if df.empty or df_metas.empty:
            return "❌ No se encontraron datos o metas para el periodo especificado."
        
        altas_logradas = df['altas'].sum()
        ingresos_logrados = df['ingresos'].sum()
        meta_altas = df_metas['altas'].sum() if 'altas' in df_metas.columns else 0
        meta_ingresos = df_metas['ingresos'].sum() if 'ingresos' in df_metas.columns else 0
        
        if meta_altas == 0 or meta_ingresos == 0:
            return "❌ No se encontraron metas definidas para el periodo especificado."
        
        cumplimiento_altas = (altas_logradas / meta_altas * 100) if meta_altas > 0 else 0
        cumplimiento_ingresos = (ingresos_logrados / meta_ingresos * 100) if meta_ingresos > 0 else 0
        
        estado_altas = "🟢 Cerca de la meta" if cumplimiento_altas >= 80 else "🟡 A mitad de camino" if cumplimiento_altas >= 50 else "🔴 Lejos de la meta"
        estado_ingresos = "🟢 Cerca de la meta" if cumplimiento_ingresos >= 80 else "🟡 A mitad de camino" if cumplimiento_ingresos >= 50 else "🔴 Lejos de la meta"
        
        periodo_msg = self._construir_mensaje_periodo(pregunta)

        if aliado:
            return (
                f"🎯 Predicción de cumplimiento para **{aliado}**{periodo_msg}:\n"
                f"- Altas: {cumplimiento_altas:.1f}% ({altas_logradas:,.0f} / {meta_altas:,.0f}) → {estado_altas}\n"
                f"- Ingresos: {cumplimiento_ingresos:.1f}% (S/ {ingresos_logrados:,.2f} / S/ {meta_ingresos:,.2f}) → {estado_ingresos}"
            )
        else:
            return (
                f"🎯 Predicción de cumplimiento global{periodo_msg}:\n"
                f"- Altas: {cumplimiento_altas:.1f}% ({altas_logradas:,.0f} / {meta_altas:,.0f}) → {estado_altas}\n"
                f"- Ingresos: {cumplimiento_ingresos:.1f}% (S/ {ingresos_logrados:,.2f} / S/ {meta_ingresos:,.2f}) → {estado_ingresos}"
            )

    def comparar_periodos(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        df_2024 = df[df['mes'].astype(str).str.contains('2024', case=False, na=False)]
        df_2025 = df[df['mes'].astype(str).str.contains('2025', case=False, na=False)]
        
        if df_2024.empty or df_2025.empty:
            return "❌ No se encontraron datos suficientes para comparar periodos."
        
        altas_2024 = df_2024['altas'].sum()
        altas_2025 = df_2025['altas'].sum()
        ingresos_2024 = df_2024['ingresos'].sum()
        ingresos_2025 = df_2025['ingresos'].sum()
        
        variacion_altas = ((altas_2025 - altas_2024) / altas_2024 * 100) if altas_2024 > 0 else 0
        variacion_ingresos = ((ingresos_2025 - ingresos_2024) / ingresos_2024 * 100) if ingresos_2024 > 0 else 0
        
        mejor_altas = "2025" if altas_2025 > altas_2024 else "2024"
        mejor_ingresos = "2025" if ingresos_2025 > ingresos_2024 else "2024"
        
        if aliado:
            return (
                f"🆚 Comparación 2024 vs 2025 para **{aliado}**:\n"
                f"- Altas 2024: {altas_2024:,.0f}\n"
                f"- Altas 2025: {altas_2025:,.0f} ({variacion_altas:+.1f}%)\n"
                f"- Ingresos 2024: S/ {ingresos_2024:,.2f}\n"
                f"- Ingresos 2025: S/ {ingresos_2025:,.2f} ({variacion_ingresos:+.1f}%)\n"
                f"→ Mejor en altas: {mejor_altas}\n"
                f"→ Mejor en ingresos: {mejor_ingresos}"
            )
        else:
            return (
                f"🆚 Comparación global 2024 vs 2025:\n"
                f"- Altas 2024: {altas_2024:,.0f}\n"
                f"- Altas 2025: {altas_2025:,.0f} ({variacion_altas:+.1f}%)\n"
                f"- Ingresos 2024: S/ {ingresos_2024:,.2f}\n"
                f"- Ingresos 2025: S/ {ingresos_2025:,.2f} ({variacion_ingresos:+.1f}%)\n"
                f"→ Mejor en altas: {mejor_altas}\n"
                f"→ Mejor en ingresos: {mejor_ingresos}"
            )

    def _construir_mensaje_periodo(self, pregunta):
        """Construye mensaje descriptivo del periodo basado en la pregunta"""
        pregunta_lower = pregunta.lower()
        
        for mes_nombre in self.meses.keys():
            if mes_nombre in pregunta_lower:
                for year in ['2024', '2025']:
                    if year in pregunta:
                        return f" para {mes_nombre.capitalize()} {year}"
                return f" para {mes_nombre.capitalize()} 2025"  # Año por defecto
        
        for year in ['2024', '2025']:
            if year in pregunta:
                return f" para el año {year}"
                
        return ""