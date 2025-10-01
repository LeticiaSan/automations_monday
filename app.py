from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔐 Configurações
API_URL = "https://api.monday.com/v2"
API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQyNDM2NzQzMSwiYWFpIjoxMSwidWlkIjo2NjYzNDU4MiwiaWFkIjoiMjAyNC0xMC0xNlQxNDozNjo1Mi4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MjA1NTk3MTcsInJnbiI6InVzZTEifQ.-tL7KnWSMYNrJkZr_eK96abjaypzpjKcBoMe-qndKVk"  # melhor deixar no ambiente
headers = {"Authorization": API_KEY}

@app.route("/turno-update", methods=["POST"])
print(">> chegou requisição turno-update!!")
def turno_update():
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    print("📩 Payload recebido:", data)

    # 🔑 Se for teste inicial do Monday (challenge)
    if "challenge" in data:
        print("⚡ Challenge recebido do Monday:", data["challenge"])
        return jsonify({"challenge": data["challenge"]}), 200

    if "event" not in data:
        print("ℹ️ Evento sem 'event', provavelmente teste de conexão.")
        return jsonify({"status": "ok", "msg": "Teste de conexão recebido"}), 200

    try:
        item_id = data["event"]["pulseId"]
        board_id = data["event"]["boardId"]
        turno = data["event"]["value"]["label"]["text"]  # valor da coluna "Turno"
        print(f"✅ Evento capturado: item={item_id}, board={board_id}, turno={turno}")
    except Exception as e:
        print("❌ Erro ao extrair dados do payload:", e)
        return jsonify({"erro": f"payload inesperado: {e}", "data": data}), 400

    # 🔄 Mapear coluna correta do encarregado conforme turno
    if turno == "Manhã":
        col_encarregado = "text_mkvwhks5"   # Encarregado Manhã
    elif turno == "Noite":
        col_encarregado = "text_mkw62geq"   # Encarregado Noite
    else:
        print("⚠️ Turno não é 'Manhã' ou 'Noite', nenhuma ação tomada.")
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
    print("📤 Enviando query para buscar encarregado:", query)

    r = requests.post(API_URL, json={"query": query}, headers=headers).json()
    print("📥 Resposta da query:", r)

    try:
        encarregado = r["data"]["items"][0]["column_values"][0]["text"]
    except Exception as e:
        print("❌ Erro ao extrair encarregado da resposta:", e)
        return jsonify({"erro": f"Falha ao pegar encarregado: {e}", "resposta": r}), 400

    if not encarregado:
        print("⚠️ Nenhum encarregado definido na coluna:", col_encarregado)
        return jsonify({"status": "Sem encarregado definido"}), 200

    print(f"👷 Encarregado encontrado: {encarregado}")

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
    print("📤 Enviando mutation para atualizar encarregado:", mutation)

    res = requests.post(API_URL, json={"query": mutation}, headers=headers).json()
    print("📥 Resposta da mutation:", res)

    return jsonify({"status": "ok", "turno": turno, "encarregado": encarregado}), 200


@app.route("/", methods=["GET"])
def home():
    return "Webhook ativo 🚀"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

