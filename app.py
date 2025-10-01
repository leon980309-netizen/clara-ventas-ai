from flask import Flask, request, jsonify, send_from_directory
import os
import threading
import time

app = Flask(__name__, static_folder='.')

# Variables globales - CARGAR AL INICIO
engine = None
sessions = {}
data_loaded = False
load_error = None
load_start_time = None

def initialize_engine():
    """Función para inicializar el motor en segundo plano con timeout"""
    global engine, data_loaded, load_error, load_start_time
    
    load_start_time = time.time()
    
    try:
        print("🚀 INICIANDO CARGA DE DATOS EN SEGUNDO PLANO...")
        print("📁 Buscando archivos CSV...")
        
        # Listar archivos disponibles
        archivos = os.listdir('.')
        csv_files = [f for f in archivos if f.endswith('.csv')]
        print(f"📋 Archivos CSV encontrados: {csv_files}")
        
        # Importar aquí para evitar dependencias circulares
        from data_loader import cargar_datos
        from analysis_engine import AnalysisEngine
        
        # Cargar datos - SOLO 2025 PARA OPTIMIZAR MEMORIA
        print("🔄 Cargando datos desde CSV...")
        df_consolidado, df_metas = cargar_datos()
        
        # Verificar que se cargaron datos
        if df_consolidado.empty:
            raise Exception("No se pudieron cargar datos de consolidado")
        if df_metas.empty:
            raise Exception("No se pudieron cargar datos de metas")
            
        print("🔧 Inicializando motor de análisis...")
        engine = AnalysisEngine(df_consolidado, df_metas)
        data_loaded = True
        
        tiempo_carga = time.time() - load_start_time
        print(f"✅ DATOS Y MOTOR CARGADOS EXITOSAMENTE en {tiempo_carga:.1f} segundos")
        print(f"📊 Registros cargados: {len(df_consolidado)} consolidado, {len(df_metas)} metas")
        
    except Exception as e:
        load_error = str(e)
        data_loaded = False
        tiempo_error = time.time() - load_start_time
        print(f"❌ ERROR CRÍTICO AL CARGAR DATOS después de {tiempo_error:.1f}s: {e}")
        print("💡 Posibles soluciones:")
        print("   - Verificar que los archivos CSV existan")
        print("   - Reducir tamaño de archivos CSV")
        print("   - Revisar formato de archivos CSV")

# Iniciar carga inmediatamente al importar el módulo
print("🎬 INICIANDO APLICACIÓN CLARA IA...")
print("🔄 Iniciando carga de datos en segundo plano...")
init_thread = threading.Thread(target=initialize_engine)
init_thread.daemon = True
init_thread.start()

@app.route('/')
def serve_index():
    """Servir la página principal"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Servir archivos estáticos"""
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal del chat"""
    global engine, data_loaded, load_error
    
    # Verificar si los datos están cargados
    if not data_loaded:
        if load_error:
            return jsonify({
                "content": f"❌ Error cargando datos: {load_error}\n\n🔧 Por favor, contacta al administrador o recarga la página."
            })
        else:
            tiempo_espera = time.time() - load_start_time if load_start_time else 0
            return jsonify({
                "content": f"⏳ Los datos aún se están cargando ({tiempo_espera:.0f}s)...\n\nPor favor, espera unos segundos y vuelve a intentar."
            })
    
    # Obtener datos del request
    data = request.get_json()
    if not data:
        return jsonify({"content": "❌ Error: No se recibieron datos"})
        
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"content": "❌ Por favor, escribe un mensaje"})

    # Manejar autenticación por IP
    user_ip = request.remote_addr
    user_info = sessions.get(user_ip)

    if not user_info:
        # Intentar autenticación
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
                        "content": f"✅ ¡Hola {username}! 👋\n\nYa puedes hacerme preguntas sobre:\n• 📊 Desempeño y ventas\n• 🎯 Cumplimiento de metas\n• 📈 Comparaciones entre periodos\n• 💰 Ingresos y altas\n\nEjemplos:\n\"¿Cómo le fue a CLARO en enero?\"\n\"Predicción de cumplimiento para ABAI\"\n\"Comparar ventas de diferentes meses\""
                    })
                else:
                    return jsonify({
                        "content": "❌ Usuario o contraseña incorrectos\n\nEjemplo: CLARO 1198"
                    })
            except Exception as e:
                print(f"🔐 Error en autenticación: {e}")
                return jsonify({
                    "content": "❌ Error en el sistema de autenticación"
                })
        
        return jsonify({
            "content": "🔐 **Autenticación Requerida**\n\nPor favor, ingresa tu usuario y contraseña:\n\nEjemplo: `CLARO 1198`\n\nUsuarios disponibles:\n- CLARO, ABAI, ATENTO, BRM, COS, etc."
        })

    # Procesar mensaje del usuario autenticado
    try:
        print(f"💬 Mensaje de {user_info['username']}: {message}")
        respuesta = engine.responder(message, user_info)
        return jsonify({"content": respuesta})
        
    except Exception as e:
        print(f"❌ Error al procesar mensaje: {e}")
        return jsonify({
            "content": "❌ Ocurrió un error al procesar tu solicitud.\n\nPor favor, intenta con otra pregunta o contacta al administrador."
        })

@app.route('/status')
def status():
    """Endpoint para verificar el estado de la aplicación"""
    global data_loaded, load_error, load_start_time, sessions
    
    tiempo_transcurrido = time.time() - load_start_time if load_start_time else 0
    estado = {
        "data_loaded": data_loaded,
        "load_error": load_error,
        "load_time_seconds": round(tiempo_transcurrido, 1),
        "sessions_active": len(sessions),
        "users_connected": list(sessions.keys())
    }
    
    return jsonify(estado)

@app.route('/health')
def health():
    """Endpoint simple de health check"""
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route('/debug')
def debug():
    """Endpoint de debug para desarrollo"""
    archivos = os.listdir('.')
    csv_files = [f for f in archivos if f.endswith('.csv')]
    
    debug_info = {
        "archivos_csv": csv_files,
        "data_loaded": data_loaded,
        "load_error": load_error,
        "sessions_count": len(sessions),
        "current_directory": os.getcwd()
    }
    
    return jsonify(debug_info)

# Manejo de errores global
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    print("🌐 INICIANDO SERVIDOR FLASK...")
    print("📍 La aplicación estará disponible en http://localhost:10000")
    print("🔍 Puedes verificar el estado en /status")
    app.run(host='0.0.0.0', port=10000, debug=False)