from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from passlib.context import CryptContext
import psycopg2
import os
import pytz
from jose import jwt
app = FastAPI()
# =========================
# 🔐 CONFIG LOGIN
# =========================
SECRET_KEY = "SUPER_SECRET_KEY_123"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# =========================
# 🌍 TIMEZONE
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
# 🔐 PEGAR USER DO TOKEN
# =========================
def get_user_id(authorization: str = Header(None)):
   try:
       if not authorization:
           return None
       token = authorization.replace("Bearer ", "")
       payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
       return payload.get("user_id")
   except:
       return None
# =========================
# 🟢 HEALTHCHECK
# =========================
@app.get("/")
def home():
   return {"status": "ok"}
# =========================
# 🔑 GERAR HASH
# =========================
@app.get("/hash")
def gerar_hash(senha: str):
   return {"hash": pwd_context.hash(senha)}
# =========================
# 📝 REGISTER
# =========================
@app.post("/register")
def register(data: dict):
   conn = None
   cur = None
   try:
       conn = get_conn()
       cur = conn.cursor()
       senha_hash = pwd_context.hash(data.get("senha"))
       cur.execute("""
           INSERT INTO estacionamento.users (nome, email, senha)
           VALUES (%s, %s, %s)
           RETURNING id
       """, (
           data.get("nome"),
           data.get("email"),
           senha_hash
       ))
       user_id = cur.fetchone()[0]
       conn.commit()
       return {"ok": True, "user_id": user_id}
   except Exception as e:
       return {"erro": str(e)}
   finally:
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 🔐 LOGIN
# =========================
@app.post("/login")
def login(data: dict):
   conn = None
   cur = None
   try:
       conn = get_conn()
       cur = conn.cursor()
       email = data.get("email")
       senha_input = data.get("senha")
       cur.execute("SELECT id, senha FROM estacionamento.users WHERE email = %s", (email,))
       user = cur.fetchone()
       if not user:
           return {"erro": "Usuário não encontrado"}
       user_id, senha_db = user
       senha_valida = False
       try:
           if pwd_context.verify(senha_input, senha_db):
               senha_valida = True
       except:
           pass
       if not senha_valida and senha_input == senha_db:
           senha_valida = True
       if not senha_valida:
           return {"erro": "Senha inválida"}
       token = jwt.encode({"user_id": user_id}, SECRET_KEY, algorithm=ALGORITHM)
       return {"token": token}
   except Exception as e:
       print("❌ ERRO LOGIN:", str(e))
       return {"erro": str(e)}
   finally:
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 🟢 ENTRADA
# =========================
@app.post("/entrada")
def entrada(data: dict, authorization: str = Header(None)):
   conn = None
   cur = None
   try:
       user_id = get_user_id(authorization)
       conn = get_conn()
       cur = conn.cursor()
       now = datetime.now(tz)
       placa = data.get("placa")
       if not placa:
           return {"erro": "Placa obrigatória"}
       marca = data.get("marca", "N/A")
       modelo = data.get("modelo", "N/A")
       tipo = data.get("tipo_veiculo", "pequeno")
       cur.execute("""
           INSERT INTO estacionamento.tickets
           (placa, marca, modelo, tipo_veiculo, data_entrada, status, user_id)
           VALUES (%s, %s, %s, %s, %s, 'ativo', %s)
           RETURNING id
       """, (placa, marca, modelo, tipo, now, user_id))
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
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 🔴 SAÍDA
# =========================
@app.post("/saida")
def saida(data: dict, authorization: str = Header(None)):
   conn = None
   cur = None
   try:
       user_id = get_user_id(authorization)
       conn = get_conn()
       cur = conn.cursor()
       ticket_id = data.get("ticket_id")
       placa = data.get("placa")
       if ticket_id:
           cur.execute("""
               SELECT id, tipo_veiculo, data_entrada, placa, marca, modelo
               FROM estacionamento.tickets
               WHERE id = %s AND status = 'ativo' AND user_id = %s
           """, (ticket_id, user_id))
       elif placa:
           cur.execute("""
               SELECT id, tipo_veiculo, data_entrada
               FROM estacionamento.tickets
               WHERE placa = %s AND status = 'ativo' AND user_id = %s
               ORDER BY data_entrada DESC
               LIMIT 1
           """, (placa, user_id))
       else:
           return {"erro": "Informe ticket_id ou placa"}
       ticket = cur.fetchone()
       if not ticket:
           return {"erro": "Ticket não encontrado"}
       ticket_id, tipo, entrada, placa, marca, modelo = ticket
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
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 📊 RELATÓRIOS
# =========================
@app.post("/relatorios")
def relatorios(filtro: dict, authorization: str = Header(None)):
   conn = None
   cur = None
   try:
       user_id = get_user_id(authorization)
       conn = get_conn()
       cur = conn.cursor()
       data_inicio = filtro.get("data_inicio")
       data_fim = filtro.get("data_fim")
       tipo = filtro.get("tipo")
       where = ["user_id = %s"]
       params = [user_id]
       if data_inicio:
           where.append("data_entrada >= %s")
           params.append(data_inicio)
       if data_fim:
           where.append("data_entrada <= %s")
           params.append(data_fim)
       if tipo and tipo != "todos":
           where.append("tipo_veiculo = %s")
           params.append(tipo)
       where_sql = "WHERE " + " AND ".join(where)
       cur.execute(f"SELECT COUNT(*) FROM estacionamento.tickets {where_sql}", params)
       total_veiculos = cur.fetchone()[0]
       cur.execute(f"""
           SELECT COALESCE(SUM(valor),0)
           FROM estacionamento.tickets
           {where_sql} AND status = 'finalizado'
       """, params)
       valor_total = cur.fetchone()[0]
       return {
           "total_veiculos": total_veiculos,
           "valor_total": float(valor_total)
       }
   except Exception as e:
       print("❌ ERRO RELATORIOS:", str(e))
       return {"erro": str(e)}
   finally:
       if cur:
           cur.close()
       if conn:
           conn.close()
# =========================
# 💰 CÁLCULO
# =========================
def calcular_valor(entrada, saida, tipo):
   diff = saida - entrada
   minutos = diff.total_seconds() / 60
   horas = diff.total_seconds() / 3600
   if minutos <= 5:
       return 0
   if tipo == "moto":
       return 15
   if entrada.date() == saida.date():
       if horas <= 1:
           return 20 if tipo == "grande" else 10
       else:
           return 30 if tipo == "grande" else 20
   fechamento_dt = entrada.replace(hour=18, minute=0, second=0, microsecond=0)
   inicio = entrada if entrada > fechamento_dt else fechamento_dt
   diff_noite = saida - inicio
   horas_noite = diff_noite.total_seconds() / 3600
   base = 30 if tipo == "grande" else 20
   adicionais = int(horas_noite // 12)
   return base + (adicionais * base)
