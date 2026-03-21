from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time
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
# 🔴 SAÍDA
# =========================
@app.post("/saida")
def saida(data: dict):
   try:
       conn = get_conn()
       cur = conn.cursor()
       ticket_id = data.get("ticket_id")
       placa = data.get("placa")
       # 🔍 BUSCA
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
   diff = saida - entrada
   minutos = diff.total_seconds() / 60
   horas = diff.total_seconds() / 3600
   # tolerância
   if minutos <= 5:
       return 0
   # moto
   if tipo == "moto":
       return 15
   # mesmo dia
   if entrada.date() == saida.date():
       if horas <= 1:
           return 20 if tipo == "grande" else 10
       else:
           return 30 if tipo == "grande" else 20
   # virou o dia
   fechamento_dt = entrada.replace(hour=18, minute=0, second=0, microsecond=0)
   if entrada > fechamento_dt:
       inicio = entrada
   else:
       inicio = fechamento_dt
   diff_noite = saida - inicio
   horas_noite = diff_noite.total_seconds() / 3600
   base = 30 if tipo == "grande" else 20
   adicionais = int(horas_noite // 12)
   return base + (adicionais * base)
# =========================
# 📊 RELATÓRIOS
# =========================
@app.post("/relatorios")
def relatorios(filtro: dict):
   try:
       conn = get_conn()
       cur = conn.cursor()
       data_inicio = filtro.get("data_inicio")
       data_fim = filtro.get("data_fim")
       tipo = filtro.get("tipo")
       where = []
       params = []
       if data_inicio:
           where.append("data_entrada >= %s")
           params.append(data_inicio)
       if data_fim:
           where.append("data_entrada <= %s")
           params.append(data_fim)
       if tipo and tipo != "todos":
           where.append("tipo_veiculo = %s")
           params.append(tipo)
       where_sql = ""
       if where:
           where_sql = "WHERE " + " AND ".join(where)
       # 🚗 total veículos
       cur.execute(f"""
           SELECT COUNT(*)
           FROM estacionamento.tickets
           {where_sql}
       """, params)
       total_veiculos = cur.fetchone()[0]
       # 💰 faturamento (corrigido)
       where_fat = where.copy()
       params_fat = params.copy()
       where_fat.append("status = 'finalizado'")
       where_fat_sql = "WHERE " + " AND ".join(where_fat)
       cur.execute(f"""
           SELECT COALESCE(SUM(valor),0)
           FROM estacionamento.tickets
           {where_fat_sql}
       """, params_fat)
       valor_total = cur.fetchone()[0] or 0
       # ⏰ por hora
       cur.execute(f"""
           SELECT EXTRACT(HOUR FROM data_entrada), COUNT(*)
           FROM estacionamento.tickets
           {where_sql}
           GROUP BY 1
           ORDER BY 1
       """, params)
       por_hora = [
           {"hora": int(h), "total": t}
           for h, t in cur.fetchall()
       ]
       # 📅 por dia
       cur.execute(f"""
           SELECT DATE(data_entrada), COUNT(*)
           FROM estacionamento.tickets
           {where_sql}
           GROUP BY 1
           ORDER BY 1
       """, params)
       por_dia = [
           {"data": str(d), "total": t}
           for d, t in cur.fetchall()
       ]
       # 🏆 top marcas
       cur.execute(f"""
           SELECT marca, COUNT(*)
           FROM estacionamento.tickets
           {where_sql}
           GROUP BY marca
           ORDER BY COUNT(*) DESC
           LIMIT 5
       """, params)
       por_marca = [
           {"marca": m, "total": t}
           for m, t in cur.fetchall()
       ]
       return {
           "total_veiculos": total_veiculos,
           "valor_total": float(valor_total),
           "por_hora": por_hora,
           "por_dia": por_dia,
           "por_marca": por_marca
       }
   except Exception as e:
       print("❌ ERRO RELATORIOS:", str(e))
       return {"erro": str(e)}
   finally:
       cur.close()
       conn.close()
