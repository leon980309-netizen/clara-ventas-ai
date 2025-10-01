from flask import Flask, request, jsonify, send_from_directory
import os
import threading

app = Flask(__name__, static_folder='.')

# Variables globales - CARGAR AL INICIO
engine = None
sessions = {}
data_loaded = False
load_error = None

def initialize_engine():
    """Función para inicializar el motor en segundo plano"""
    global engine, data_loaded, load_error
    
    try:
        print("🚀 Iniciando carga de datos...")
        
        # Importar aquí para evitar dependencias circulares
        from data_loader import cargar_datos
        from analysis_engine import AnalysisEngine
        
        # Cargar datos - AHORA CON 4 ARCHIVOS CSV
        df_consolidado, df_metas = cargar_datos()
        engine = AnalysisEngine(df_consolidado, df_metas)
        data_loaded = True
        print("✅ Datos y motor cargados exitosamente")
        
    except Exception as e:
        print(f"❌ Error crítico al cargar datos: {e}")
        load_error = str(e)
        data_loaded = False

# Iniciar carga inmediatamente al importar el módulo
print("🔄 Iniciando carga de datos en segundo plano...")
init_thread = threading.Thread(target=initialize_engine)
init_thread.daemon = True
init_thread.start()

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    global engine, data_loaded, load_error
    
    # Verificar si los datos están cargados
    if not data_loaded:
        if load_error:
            return jsonify({
                "content": f"❌ Error cargando datos: {load_error}. Por favor, recarga la página."
            })
        else:
            return jsonify({
                "content": "⏳ Los datos aún se están cargando. Por favor, espera unos segundos y vuelve a intentar."
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

@app.route('/status')
def status():
    """Endpoint para verificar el estado de la carga"""
    return jsonify({
        "data_loaded": data_loaded,
        "load_error": load_error,
        "sessions_active": len(sessions)
    })