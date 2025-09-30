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
        pregunta_lower = pregunta.lower().strip()
        
        for mes_nombre, mes_num in self.meses.items():
            if mes_nombre in pregunta_lower:
                # Buscar año explícito: "septiembre 2025" o "septiembre de 2025"
                patron = rf"{mes_nombre}\s*(?:de\s*)?(\d{{4}})"
                match = re.search(patron, pregunta_lower)
                if match:
                    año = match.group(1)
                    # Filtrar por año y mes (admite formatos como "2025-09", "09/2025", "Septiembre 2025")
                    def filtro(df):
                        return df[
                            df['mes'].astype(str).str.contains(f"{año}.*{mes_num}", case=False, na=False) |
                            df['mes'].astype(str).str.contains(f"{mes_num}.*{año}", case=False, na=False)
                        ]
                    return filtro
                else:
                    # Si no hay año, asumir 2025 (el año más reciente en tus datos)
                    def filtro(df):
                        return df[
                            df['mes'].astype(str).str.contains(r"2025.*" + mes_num, case=False, na=False) |
                            df['mes'].astype(str).str.contains(mes_num + r".*2025", case=False, na=False)
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
            return "Lo siento, no entendí. Puedo ayudarte con desempeño, predicción, comparación."

    def analizar_desempenio(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        filtro_periodo = self.detectar_periodo(pregunta)
        if filtro_periodo:
            df = filtro_periodo(df)
        
        total_altas = df['altas'].sum()
        total_ingresos = df['ingresos'].sum()
        
        # Construir mensaje de periodo
        periodo_msg = ""
        if 'septiembre 2025' in pregunta.lower() or ('septiembre' in pregunta.lower() and '2025' in pregunta.lower()):
            periodo_msg = " para septiembre 2025"
        elif 'septiembre 2024' in pregunta.lower() or ('septiembre' in pregunta.lower() and '2024' in pregunta.lower()):
            periodo_msg = " para septiembre 2024"
        elif 'septiembre' in pregunta.lower():
            periodo_msg = " para septiembre 2025"
        # Puedes agregar más meses si lo deseas

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
        
        altas_logradas = df['altas'].sum()
        ingresos_logrados = df['ingresos'].sum()
        meta_altas = df_metas['altas'].sum() if 'altas' in df_metas.columns else 0
        meta_ingresos = df_metas['ingresos'].sum() if 'ingresos' in df_metas.columns else 0
        
        cumplimiento_altas = (altas_logradas / meta_altas * 100) if meta_altas > 0 else 0
        cumplimiento_ingresos = (ingresos_logrados / meta_ingresos * 100) if meta_ingresos > 0 else 0
        
        estado_altas = "🟢 Cerca de la meta" if cumplimiento_altas >= 80 else "🔴 Lejos de la meta"
        estado_ingresos = "🟢 Cerca de la meta" if cumplimiento_ingresos >= 80 else "🔴 Lejos de la meta"
        
        periodo_msg = ""
        if 'septiembre 2025' in pregunta.lower() or ('septiembre' in pregunta.lower() and '2025' in pregunta.lower()):
            periodo_msg = " para septiembre 2025"
        elif 'septiembre 2024' in pregunta.lower() or ('septiembre' in pregunta.lower() and '2024' in pregunta.lower()):
            periodo_msg = " para septiembre 2024"
        elif 'septiembre' in pregunta.lower():
            periodo_msg = " para septiembre 2025"

        if aliado:
            return (
                f"🎯 Predicción de cumplimiento para **{aliado}**{periodo_msg}:\n"
                f"- Altas: {cumplimiento_altas:.1f}% → {estado_altas}\n"
                f"- Ingresos: {cumplimiento_ingresos:.1f}% → {estado_ingresos}"
            )
        else:
            return (
                f"🎯 Predicción de cumplimiento global{periodo_msg}:\n"
                f"- Altas: {cumplimiento_altas:.1f}% → {estado_altas}\n"
                f"- Ingresos: {cumplimiento_ingresos:.1f}% → {estado_ingresos}"
            )

    def comparar_periodos(self, aliado, pregunta):
        df = self.filtrar_por_aliado(self.df, aliado)
        df_2024 = df[df['mes'].astype(str).str.contains('2024', case=False, na=False)]
        df_2025 = df[df['mes'].astype(str).str.contains('2025', case=False, na=False)]
        
        altas_2024 = df_2024['altas'].sum()
        altas_2025 = df_2025['altas'].sum()
        mejor = "2025" if altas_2025 > altas_2024 else "2024"
        
        if aliado:
            return (
                f"🆚 Comparación 2024 vs 2025 para **{aliado}**:\n"
                f"- Altas 2024: {altas_2024:,.0f}\n"
                f"- Altas 2025: {altas_2025:,.0f}\n"
                f"→ Mejor desempeño en: {mejor}"
            )
        else:
            return (
                f"🆚 Comparación global 2024 vs 2025:\n"
                f"- Altas 2024: {altas_2024:,.0f}\n"
                f"- Altas 2025: {altas_2025:,.0f}\n"
                f"→ Mejor desempeño en: {mejor}"
            )