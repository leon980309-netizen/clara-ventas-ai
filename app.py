from flask import Flask, request, jsonify, render_template
import os

from claro_sales_ai import ClaraIA

app = Flask(__name__)

# URLs de Google Drive (asegúrate de que sean públicas y descargables)
URL_CONSOLIDADO = os.environ.get("URL_CONSOLIDADO", "https://drive.google.com/uc?export=download&id=1AA2W0IfqZVPH69yveeTdAYCu30GOvqSK")
URL_METAS = os.environ.get("URL_METAS", "https://drive.google.com/uc?export=download&id=1Nc-dpGnbFT3qZ2qpYZGZoL0IFTgku4Fc")

clara_ia = None
try:
    print("🔄 Inicializando Clara IA con Groq y datos reales...")
    clara_ia = ClaraIA(URL_CONSOLIDADO, URL_METAS)
    print("✅ Clara IA lista.")
except Exception as e:
    print(f"❌ Error al iniciar: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    global clara_ia
    if clara_ia is None:
        return jsonify({"content": "❌ Clara IA no disponible."}), 500

    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"content": "⚠️ Por favor, escribe una pregunta."}), 400

    try:
        response = clara_ia.ask(msg)
        return jsonify({"content": response})
    except Exception as e:
        return jsonify({"content": f"❌ Error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)