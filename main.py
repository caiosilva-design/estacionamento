from fastapi import FastAPI
from datetime import datetime, time
import psycopg2
import os
app = FastAPI()
def get_conn():
   return psycopg2.connect(os.getenv("DATABASE_URL"))
# =========================
# 🟢 ENTRADA
# =========================
@app.post("/entrada")
def entrada(data: dict):
   conn = get_conn()
   cur = conn.cursor()
   now = datetime.now()
   cur.execute("""
       INSERT INTO estacionamento.tickets (placa, marca, modelo, tipo_veiculo, data_entrada, status)
       VALUES (%s, %s, %s, %s, %s, 'ativo')
       RETURNING id
   """, (
       data["placa"],
       data["marca"],
       data["modelo"],
       data["tipo_veiculo"],
       now
   ))
   ticket_id = cur.fetchone()[0]
   conn.commit()
   cur.close()
   conn.close()
   return {
       "ticket_id": ticket_id,
       "data_entrada": now
   }
# =========================
# 🔴 SAÍDA
# =========================
@app.post("/saida")
def saida(data: dict):
   conn = get_conn()
   cur = conn.cursor()
   # buscar ticket
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
   # atualizar
   cur.execute("""
       UPDATE estacionamento.tickets
       SET data_saida = %s, valor = %s, status = 'finalizado'
       WHERE id = %s
   """, (now, valor, ticket_id))
   conn.commit()
   cur.close()
   conn.close()
   return {
       "ticket_id": ticket_id,
       "valor": valor,
       "saida": now
   }
# =========================
# 💰 LÓGICA DE PREÇO
# =========================
def calcular_valor(entrada, saida, tipo):
   # horários
   fechamento = time(18, 0)
   fechamento_sabado = time(16, 0)
   is_sabado = entrada.weekday() == 5
   limite = fechamento_sabado if is_sabado else fechamento
   # diária base
   if tipo == "grande":
       diaria = 30
       hora_extra = 20
   elif tipo == "pequeno":
       diaria = 20
       hora_extra = 15
   elif tipo == "moto":
       return 15
   else:
       diaria = 20
       hora_extra = 15
   # passou do horário de fechamento
   if saida.time() > limite:
       return diaria * 2
   return diaria
