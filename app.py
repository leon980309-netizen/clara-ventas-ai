from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# Variables globales (se inicializarán en el primer request)
engine = None
sessions = {}

# Rutas de Excel
RUTAS_EXCEL = [
    "Base Consolidada 2024.xlsx",
    "Base Consolidada 2025.xlsx"
]

def init_engine():
    """Inicializa el motor de análisis (solo una vez)."""
    global engine
    if engine is not None:
        return
    
    print("⏳ Cargando datos de Excel...")
    try:
        from data_loader import cargar_datos
        from analysis_engine import AnalysisEngine
        df_consolidado, df_metas = cargar_datos(RUTAS_EXCEL)
        engine = AnalysisEngine(df_consolidado, df_metas)
        print("✅ Datos cargados correctamente.")
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")
        import traceback
        traceback.print_exc()

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    global engine, sessions
    
    # Inicializar el motor en el primer request
    if engine is None:
        init_engine()
        if engine is None:
            return jsonify({
                "content": "❌ Error crítico: No se pudieron cargar los datos. Contacta al administrador."
            })
    
    data = request.get_json()
    message = data.get('message', '').strip()

    user_ip = request.remote_addr
    user_info = sessions.get(user_ip)

    if not user_info:
        parts = message.split(maxsplit=1)
        if len(parts) == 2:
            username, password = parts[0], parts[1]
            try:
                from security import Security
                security = Security()
                user = security.login(username, password)
                if user:
                    sessions[user_ip] = user
                    return jsonify({
                        "content": f"✅ ¡Hola {username}! Ya puedes hacerme preguntas sobre desempeño, cumplimiento o comparaciones."
                    })
            except Exception as e:
                print(f"Error en autenticación: {e}")
        return jsonify({
            "content": "🔐 Por favor, ingresa tu usuario y contraseña (ej: CLARO 1198)"
        })

    try:
        respuesta = engine.responder(message, user_info)
        return jsonify({"content": respuesta})
    except Exception as e:
        print(f"Error al responder: {e}")
        return jsonify({"content": "❌ Ocurrió un error al procesar tu solicitud."})