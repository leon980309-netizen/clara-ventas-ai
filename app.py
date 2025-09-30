from flask import Flask, request, jsonify, send_from_directory
from security import Security
from data_loader import cargar_datos
from analysis_engine import AnalysisEngine

app = Flask(__name__, static_folder='.')

# Rutas de tus archivos Excel
RUTAS_EXCEL = [
    "Base Consolidada 2024.xlsx",
    "Base Consolidada 2025.xlsx"
]

print("⏳ Cargando datos de Excel...")
df_consolidado, df_metas = cargar_datos(RUTAS_EXCEL)
engine = AnalysisEngine(df_consolidado, df_metas)
print("✅ Datos cargados correctamente.")

sessions = {}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
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


if __name__ == '__main__':
    app.run(debug=False)
