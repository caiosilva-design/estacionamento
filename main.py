from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time, timedelta
import psycopg2
import os
import pytz
app = FastAPI()
# =========================
# 🌍 TIMEZONE BRASIL
# =========================
tz = pytz.timezone("America/Sao_Paulo")
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
# 🔌 BANCO
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
       now = datetime.now(tz)
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
# 🔴 SAÍDA (ID OU PLACA)
# =========================
@app.post("/saida")
def saida(data: dict):
   try:
       conn = get_conn()
       cur = conn.cursor()
       ticket_id = data.get("ticket_id")
       placa = data.get("placa")
       # 🔍 busca
       if ticket_id:
           cur.execute("""
               SELECT id, tipo_veiculo, data_entrada
               FROM estacionamento.tickets
               WHERE id = %s AND status = 'ativo'
           """, (ticket_id,))
       elif placa:
           cur.execute("""
               SELECT id, tipo_veiculo, data_entrada
               FROM estacionamento.tickets
               WHERE placa = %s AND status = 'ativo'
               ORDER BY data_entrada DESC
               LIMIT 1
           """, (placa,))
       else:
           return {"erro": "Informe ticket_id ou placa"}
       ticket = cur.fetchone()
       if not ticket:
           return {"erro": "Ticket não encontrado"}
       ticket_id, tipo, entrada = ticket
       now = datetime.now(tz)
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
# 💰 CÁLCULO
# =========================
def calcular_valor(entrada, saida, tipo):
   from datetime import timedelta, time
   # ⏱️ diferença total
   diff = saida - entrada
   minutos = diff.total_seconds() / 60
   horas = diff.total_seconds() / 3600
   # 🟢 TOLERÂNCIA
   if minutos <= 5:
       return 0
   # 🏍️ MOTO (fixo sempre)
   if tipo == "moto":
       return 15
   # 🎯 MESMO DIA
   if entrada.date() == saida.date():
       # até 1h
       if horas <= 1:
           if tipo == "grande":
               return 20
           else:
               return 10
       # mais de 1h
       else:
           if tipo == "grande":
               return 30
           else:
               return 20
   # 🔴 OUTRO DIA (virou o dia)
   else:
       fechamento = time(18, 0)
       # pega o fechamento do dia da entrada
       fechamento_dt = entrada.replace(
           hour=18,
           minute=0,
           second=0,
           microsecond=0
       )
       # se entrou depois do fechamento → usa entrada mesmo
       if entrada > fechamento_dt:
           inicio_calculo = entrada
       else:
           inicio_calculo = fechamento_dt
       diff_noite = saida - inicio_calculo
       horas_noite = diff_noite.total_seconds() / 3600
       # 💰 valor base (primeira diária)
       if tipo == "grande":
           valor = 30
       else:
           valor = 20
       # 🧮 a cada 12h adiciona diária
       adicionais = int(horas_noite // 12)
       valor += adicionais * valor
       return valor
