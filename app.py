from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)

# 🔐 Configurações
API_URL = "https://api.monday.com/v2"
API_KEY = os.environ.get("MONDAY_API_KEY")
headers = {"Authorization": API_KEY}

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@app.route("/turno-update", methods=["POST"])
def turno_update():
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    logger.info("📩 Payload recebido: %s", data)

    # 🔑 Se for teste inicial do Monday (challenge)
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]}), 200

    if "event" not in data:
        return jsonify({"status": "ok", "msg": "Teste de conexão recebido"}), 200

    try:
        item_id = data["event"]["pulseId"]
        board_id = data["event"]["boardId"]
        turno = data["event"]["value"]["label"]["text"].strip().lower()  # normaliza para minúsculas
        logger.info("➡️ Evento: item_id=%s board_id=%s turno=%s", item_id, board_id, turno)
    except Exception as e:
        return jsonify({"erro": f"payload inesperado: {e}", "data": data}), 400

    # 🔄 Mapear coluna correta do encarregado conforme turno
    if turno == "manhã":
        col_encarregado = "text_mkvwhks5"   # Encarregado Manhã
    elif turno == "noite":
        col_encarregado = "text_mkw62geq"   # Encarregado Noite
    else:
        logger.info("ℹ️ Turno sem ação: %s", turno)
        return jsonify({"status": "Turno sem ação"}), 200

    # 🔎 Buscar valor do encarregado (Manhã ou Noite)
    query = f"""
    query {{
      items(ids: {item_id}) {{
        column_values(ids: ["{col_encarregado}"]) {{
          text
        }}
      }}
    }}
    """
    r = requests.post(API_URL, json={"query": query}, headers=headers).json()
    logger.info("📡 Resposta GraphQL (query encarregado): %s", r)

    encarregado = r["data"]["items"][0]["column_values"][0]["text"]

    if not encarregado:
        logger.info("⚠️ Nenhum encarregado definido na coluna %s", col_encarregado)
        return jsonify({"status": "Sem encarregado definido"}), 200

    # ✏️ Atualizar "Encarregado Responsável"
    mutation = f"""
    mutation {{
      change_simple_column_value(
        board_id: {board_id},
        item_id: {item_id},
        column_id: "text_mkw6zqbq",  # Encarregado Responsável
        value: "{encarregado}"
      ) {{
        id
      }}
    }}
    """
    resp = requests.post(API_URL, json={"query": mutation}, headers=headers).json()
    logger.info("✅ Mutação executada. Resposta: %s", resp)

    return jsonify({"status": "ok", "turno": turno, "encarregado": encarregado}), 200


@app.route("/", methods=["GET"])
def home():
    return "Webhook ativo 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
