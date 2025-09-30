from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔐 Configurações
API_URL = "https://api.monday.com/v2"
API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQyNDM2NzQzMSwiYWFpIjoxMSwidWlkIjo2NjYzNDU4MiwiaWFkIjoiMjAyNC0xMC0xNlQxNDozNjo1Mi4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MjA1NTk3MTcsInJnbiI6InVzZTEifQ.-tL7KnWSMYNrJkZr_eK96abjaypzpjKcBoMe-qndKVk"
headers = {"Authorization": API_KEY}

@app.route("/turno-update", methods=["POST"])
def turno_update():
    data = request.json or {}

    # 🔑 Se for teste inicial do Monday (challenge)
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]}), 200

    if "event" not in data:
        return jsonify({"status": "ok", "msg": "Teste de conexão recebido"}), 200

    try:
        item_id = data["event"]["pulseId"]
        board_id = data["event"]["boardId"]
        turno = data["event"]["value"]["label"]["text"]
    except Exception as e:
        return jsonify({"erro": f"payload inesperado: {e}", "data": data}), 400

    # Definir coluna do encarregado conforme turno
    if turno == "Manhã":
        col_encarregado = "text_mkvwhks5"
    elif turno == "Noite":
        col_encarregado = "text_mkw62geq"
    else:
        return jsonify({"status": "Turno sem ação"}), 200

    # Buscar valor do encarregado
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
    encarregado = r["data"]["items"][0]["column_values"][0]["text"]

    if not encarregado:
        return jsonify({"status": "Sem encarregado definido"}), 200

    # Atualizar coluna principal
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
    requests.post(API_URL, json={"query": mutation}, headers=headers)

    return jsonify({"status": "ok", "turno": turno, "encarregado": encarregado}), 200


@app.route("/", methods=["GET"])
def home():
    return "Webhook ativo 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
