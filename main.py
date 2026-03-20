from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time, timedelta
import psycopg2
import os
app = FastAPI()
# =========================
# 🔥 CORS
# =========================
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)
# =========================
# 🔌 CONEXÃO BANCO
# =========================
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
   try:
       conn = get_conn()
       cur = conn.cursor()
       now = datetime.now()
       placa = data.get("placa")
       marca = data.get("marca", "N/A")
       modelo = data.get("modelo", "N/A")
       tipo = data.get("tipo_veiculo", "pequeno")
       if not placa:
           return {"erro": "Placa obrigatória"}
       cur.execute("""
           INSERT INTO estacionamento.tickets
           (placa, marca, modelo, tipo_veiculo, data_entrada, status)
           VALUES (%s, %s, %s, %s, %s, 'ativo')
           RETURNING id
       """, (
           placa,
           marca,
           modelo,
           tipo,
           now
       ))
       ticket_id = cur.fetchone()[0]
       conn.commit()
       return {
           "ok": True,
           "ticket_id": ticket_id,
           "entrada": now.isoformat()
       }
   except Exception as e:
       print("❌ ERRO ENTRADA:", str(e))
       return {"erro": str(e)}
   finally:
       cur.close()
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
           "ok": True,
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
# 💰 CÁLCULO DE VALOR
# =========================
def calcular_valor(entrada, saida, tipo):
   # ⏱️ TOLERÂNCIA 5 MINUTOS
   if saida - entrada <= timedelta(minutes=5):
       return 0
   fechamento = time(18, 0)
   fechamento_sabado = time(16, 0)
   is_sabado = entrada.weekday() == 5
   limite = fechamento_sabado if is_sabado else fechamento
   # 💰 VALORES
   if tipo == "grande":
       diaria = 30
   elif tipo == "pequeno":
       diaria = 20
   elif tipo == "moto":
       return 15
   else:
       diaria = 20
   # ⏱️ passou do horário
   if saida.time() > limite:
       return diaria * 2
   return diaria
