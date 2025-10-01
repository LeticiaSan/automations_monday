from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)

# 🔐 Configurações
API_URL = "https://api.monday.com/v2"
API_KEY = os.getenv("MONDAY_API_KEY", "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQyNDM2NzQzMSwiYWFpIjoxMSwidWlkIjo2NjYzNDU4MiwiaWFkIjoiMjAyNC0xMC0xNlQxNDozNjo1Mi4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MjA1NTk3MTcsInJnbiI6InVzZTEifQ.-tL7KnWSMYNrJkZr_eK96abjaypzpjKcBoMe-qndKVk")
headers = {"Authorization": API_KEY}

# 📋 Configurar logging (vai para stdout e aparece no Render)
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
        logger.info("⚡ Respondendo challenge: %s", data["challenge"])
        return jsonify({"challenge": data["challenge"]}), 200

    if "event" not in data:
        logger.warning("⚠️ Requisição recebida sem 'event'. Data: %s", data)
        return jsonify({"status": "ok", "msg": "Teste de conexão recebido"}), 200

    try:
        item_id = data["event"]["pulseId"]
        board_id = data["event"]["boardId"]
        turno = data["event"]["value"]["label"]["text"]  # valor da coluna "Turno"
        logger.info("➡️ Evento: item_id=%s board_id=%s turno=%s", item_id, board_id, turno)
    except Exception as e:
        logger.error("❌ Erro ao extrair dados do payload: %s", e, exc_info=True)
        return jsonify({"erro": f"payload inesperado: {e}", "data": data}), 400

    # 🔄 Mapear coluna correta do encarregado conforme turno
    if turno == "Manhã":
        col_encarregado = "text_mkvwhks5"   # Encarregado Manhã
    elif turno == "Noite":
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
    logger.info("📤 Enviando query GraphQL: %s", query)
    r = requests.post(API_URL, json={"query": query}, headers=headers).json()
    logger.info("📥 Resposta query: %s", r)

    encarregado = r["data"]["items"][0]["column_values"][0]["text"]

    if not encarregado:
        logger.warning("⚠️ Nenhum encarregado definido para turno %s", turno)
        return jsonify({"status": "Sem encarregado definido"}), 200

    # ✏️ Atualizar "Encarregado Responsável"
    mutation = f"""
    mutation {{
      change_simple_column_value(
        board_id: {board_id},
        item_id: {item_id},
        column_id: "text_mkw6zqbq",
        value: "{encarregado}"
      ) {{
        id
      }}
    }}
    """
    logger.info("📤 Enviando mutation GraphQL: %s", mutation)
    resp_mut = requests.post(API_URL, json={"query": mutation}, headers=headers).json()
    logger.info("📥 Resposta mutation: %s", resp_mut)

    return jsonify({"status": "ok", "turno": turno, "encarregado": encarregado}), 200


@app.route("/", methods=["GET"])
def home():
    return "Webhook ativo 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
