from flask import Flask, request, jsonify, send_from_directory
from security import Security
import os

app = Flask(__name__, static_folder='.')

# Variables globales (se inicializarán al iniciar la app)
engine = None
sessions = {}

# Rutas de tus archivos Excel
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
        return jsonify({"content": "⚠️ El sistema aún se está inicializando. Por favor, espera unos segundos y vuelve a intentar."})
    
    data = request.get_json()
    message = data.get('message', '').strip()

    user_ip = request.remote_addr
    user_info = sessions.get(user_ip)

    if not user_info:
        parts = message.split(maxsplit=1)
        if len(parts) == 2:
            username, password = parts[0], parts[1]
            security = Security()
            user = security.login(username, password)
            if user:
                sessions[user_ip] = user
                return jsonify({
                    "content": f"✅ ¡Hola {username}! Ya puedes hacerme preguntas sobre desempeño, cumplimiento o comparaciones."
                })
        return jsonify({
            "content": "🔐 Por favor, ingresa tu usuario y contraseña (ej: CLARO 1198)"
        })

    respuesta = engine.responder(message, user_info)
    return jsonify({"content": respuesta})

def init_app():
    """Inicializa los datos después de que la app esté lista."""
    global engine
    print("⏳ Cargando datos de Excel...")
    try:
        from data_loader import cargar_datos
        from analysis_engine import AnalysisEngine
        df_consolidado, df_metas = cargar_datos(RUTAS_EXCEL)
        engine = AnalysisEngine(df_consolidado, df_metas)
        print("✅ Datos cargados correctamente.")
    except Exception as e:
        print(f"❌ Error al cargar los datos: {e}")
        engine = None

if __name__ == '__main__':
    # Inicializa los datos
    init_app()
    # Usa el puerto que Render asigna
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)