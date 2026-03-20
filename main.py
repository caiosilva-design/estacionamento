from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time
import psycopg2
import os
app = FastAPI()
# 🔥 CORS (OBRIGATÓRIO)
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)
# 🔌 CONEXÃO
def get_conn():
   return psycopg2.connect(os.getenv("DATABASE_URL"))
# =========================
# 🟢 HEALTHCHECK
# =========================
@app.get("/")
def home():
   return {"status": "ok"}
# =========================
# 🟢 ENTRADA
# =========================
@app.post("/entrada")
def entrada(data: dict):
   print("🔥 DADOS RECEBIDOS:", data)
   conn = None
   cur = None
   try:
       conn = get_conn()
       cur = conn.cursor()
       now = datetime.now()
       # 🔍 pegar dados
       placa = data.get("placa")
       tipo = data.get("tipo")
       marca = data.get("marca", "N/A")
       modelo = data.get("modelo", "N/A")
       if not placa or not tipo:
           raise Exception("placa ou tipo não enviados")
       # 🔄 normalizar tipo
       if tipo == "carro_grande":
           tipo_db = "grande"
       elif tipo == "carro_pequeno":
           tipo_db = "pequeno"
       else:
           tipo_db = tipo
       print("👉 tipo convertido:", tipo_db)
       # 💾 INSERT
       cur.execute("""
           INSERT INTO estacionamento.tickets
           (placa, marca, modelo, tipo_veiculo, data_entrada, status)
           VALUES (%s, %s, %s, %s, %s, 'ativo')
           RETURNING id
       """, (
           placa,
           marca,
           modelo,
           tipo_db,
           now
       ))
       ticket_id = cur.fetchone()[0]
       conn.commit()
       print("✅ TICKET CRIADO:", ticket_id)
       return {
           "ok": True,
           "ticket_id": ticket_id,
           "data_entrada": now.isoformat()
       }
   except Exception as e:
       print("❌ ERRO BACKEND:", str(e))
       return {
           "ok": False,
           "erro": str(e)
       }
   finally:
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 🔴 SAÍDA
# =========================
@app.post("/saida")
def saida(data: dict):
   try:
       conn = get_conn()
       cur = conn.cursor()
       cur.execute("""
           SELECT id, tipo_veiculo, data_entrada
           FROM estacionamento.tickets
           WHERE id = %s AND status = 'ativo'
       """, (data["ticket_id"],))
       ticket = cur.fetchone()
       if not ticket:
           return {"erro": "Ticket não encontrado"}
       ticket_id, tipo, entrada = ticket
       now = datetime.now()
       valor = calcular_valor(entrada, now, tipo)
       cur.execute("""
           UPDATE estacionamento.tickets
           SET data_saida = %s, valor = %s, status = 'finalizado'
           WHERE id = %s
       """, (now, valor, ticket_id))
       conn.commit()
       return {
           "ticket_id": ticket_id,
           "valor": valor,
           "saida": now.isoformat()
       }
   except Exception as e:
       print("❌ ERRO SAIDA:", str(e))
       return {"erro": str(e)}
   finally:
       cur.close()
       conn.close()
# =========================
# 💰 PREÇO
# =========================
def calcular_valor(entrada, saida, tipo):
   fechamento = time(18, 0)
   fechamento_sabado = time(16, 0)
   is_sabado = entrada.weekday() == 5
   limite = fechamento_sabado if is_sabado else fechamento
   if tipo == "grande":
       diaria = 30
   elif tipo == "pequeno":
       diaria = 20
   elif tipo == "moto":
       return 15
   else:
       diaria = 20
   if saida.time() > limite:
       return diaria * 2
   return diaria
