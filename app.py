from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='.')

# Variables globales
engine = None
sessions = {}

# Rutas de Excel
RUTAS_EXCEL = [
    "Base Consolidada 2024.xlsx",
    "Base Consolidada 2025.xlsx"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    global engine, sessions
    
    if engine is None:
        return jsonify({"content": "⚠️ Inicializando sistema. Por favor, espera 10 segundos y vuelve a intentar."})
    
    # ... resto de tu lógica de chat ...

def init_engine():
    """Inicializa el motor de análisis en segundo plano."""
    global engine
    print("⏳ Cargando datos de Excel...")
    try:
        from security import Security
        from data_loader import cargar_datos
        from analysis_engine import AnalysisEngine
        df_consolidado, df_metas = cargar_datos(RUTAS_EXCEL)
        engine = AnalysisEngine(df_consolidado, df_metas)
        print("✅ Datos cargados correctamente.")
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")

if __name__ == '__main__':
    # Inicia el servidor INMEDIATAMENTE
    port = int(os.environ.get("PORT", 5000))
    
    # Inicia la carga de datos en segundo plano
    import threading
    threading.Thread(target=init_engine, daemon=True).start()
    
    # Inicia el servidor Flask
    app.run(host="0.0.0.0", port=port, debug=False)