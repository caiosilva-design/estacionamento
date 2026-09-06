# 🚗 API de Estacionamento

API REST desenvolvida com **FastAPI** para gerenciamento de estacionamento, incluindo cadastro de usuários, autenticação, entrada e saída de veículos, cálculo de tarifas e geração de relatórios.

## 📋 Funcionalidades

* 🔐 Cadastro de usuários
* 🔑 Login com autenticação JWT
* 🔒 Hash de senhas utilizando bcrypt
* 🚗 Registro de entrada de veículos
* 🏁 Registro de saída de veículos
* 💰 Cálculo automático do valor do estacionamento
* 📊 Relatórios de movimentação
* 🕐 Controle de horário utilizando o fuso `America/Sao_Paulo`
* 🗄️ Integração com PostgreSQL
* 🌐 Configuração de CORS
* ❤️ Endpoint de health check

---

## 🛠️ Tecnologias utilizadas

* **Python**
* **FastAPI**
* **Uvicorn**
* **PostgreSQL**
* **psycopg2**
* **JWT**
* **Passlib**
* **bcrypt**
* **pytz**

---

## 📁 Estrutura esperada

```text
projeto/
├── main.py
├── requirements.txt
└── README.md
```

O arquivo principal da API pode ser chamado de `main.py`.

---

## ⚙️ Requisitos

Antes de executar o projeto, tenha instalado:

* Python 3.10+
* PostgreSQL
* `pip`

---

## 📦 Instalação

Clone o projeto:

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_PROJETO>
```

Crie um ambiente virtual:

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 🔐 Variável de ambiente

A API utiliza a variável de ambiente `DATABASE_URL` para realizar a conexão com o PostgreSQL.

Exemplo:

```text
DATABASE_URL=postgresql://usuario:senha@localhost:5432/estacionamento
```

### Windows PowerShell

```powershell
$env:DATABASE_URL="postgresql://usuario:senha@localhost:5432/estacionamento"
```

### Linux / macOS

```bash
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/estacionamento"
```

> ⚠️ Não coloque credenciais reais do banco diretamente no código ou no repositório.

---

## 🗄️ Banco de dados

A API espera que exista o schema:

```sql
estacionamento
```

E as tabelas:

```text
estacionamento.users
estacionamento.tickets
```

### Tabela `users`

Estrutura mínima esperada:

```sql
CREATE SCHEMA IF NOT EXISTS estacionamento;

CREATE TABLE estacionamento.users (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha TEXT NOT NULL
);
```

### Tabela `tickets`

Estrutura mínima esperada:

```sql
CREATE TABLE estacionamento.tickets (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(20) NOT NULL,
    marca VARCHAR(100),
    modelo VARCHAR(100),
    tipo_veiculo VARCHAR(30) NOT NULL,
    data_entrada TIMESTAMP NOT NULL,
    data_saida TIMESTAMP,
    valor NUMERIC(10,2),
    status VARCHAR(30) NOT NULL,
    user_id INTEGER REFERENCES estacionamento.users(id)
);
```

---

## ▶️ Executando a API

Inicie o servidor com:

```bash
uvicorn main:app --reload
```

Por padrão, a API ficará disponível em:

```text
http://127.0.0.1:8000
```

A documentação automática do FastAPI pode ser acessada em:

```text
http://127.0.0.1:8000/docs
```

Também está disponível a documentação alternativa:

```text
http://127.0.0.1:8000/redoc
```

---

# 🔌 Endpoints

## ❤️ Health Check

### `GET /`

Verifica se a API está funcionando.

### Resposta

```json
{
    "status": "ok"
}
```

---

## 🔑 Gerar hash de senha

### `GET /hash`

Gera um hash bcrypt para uma senha.

### Parâmetro

```text
senha
```

Exemplo:

```text
GET /hash?senha=123456
```

### Resposta

```json
{
    "hash": "$2b$..."
}
```

> ⚠️ Esse endpoint é útil para testes, mas não é recomendado mantê-lo exposto em produção, pois permite que qualquer pessoa envie uma senha para ser processada.

---

# 👤 Usuários

## 📝 Registrar usuário

### `POST /register`

Cria um novo usuário.

### Body

```json
{
    "nome": "João da Silva",
    "email": "joao@email.com",
    "senha": "123456"
}
```

### Resposta

```json
{
    "ok": true,
    "user_id": 1
}
```

A senha é armazenada utilizando hash bcrypt.

---

## 🔐 Login

### `POST /login`

Realiza a autenticação do usuário.

### Body

```json
{
    "email": "joao@email.com",
    "senha": "123456"
}
```

### Resposta

```json
{
    "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

O token retornado deve ser enviado nas requisições protegidas utilizando:

```http
Authorization: Bearer SEU_TOKEN
```

---

# 🚗 Entrada de veículo

## `POST /entrada`

Registra a entrada de um veículo no estacionamento.

### Header

```http
Authorization: Bearer SEU_TOKEN
```

### Body

```json
{
    "placa": "ABC1D23",
    "marca": "Toyota",
    "modelo": "Corolla",
    "tipo_veiculo": "pequeno"
}
```

### Tipos de veículo

A aplicação trabalha atualmente com:

```text
pequeno
grande
moto
```

### Resposta

```json
{
    "ok": true,
    "ticket_id": 10,
    "entrada": "2026-09-06T19:00:00-03:00"
}
```

---

# 🏁 Saída de veículo

## `POST /saida`

Finaliza um ticket ativo e calcula automaticamente o valor a pagar.

A busca pode ser realizada pelo `ticket_id` ou pela `placa`.

### Utilizando ticket

```json
{
    "ticket_id": 10
}
```

### Utilizando placa

```json
{
    "placa": "ABC1D23"
}
```

### Header

```http
Authorization: Bearer SEU_TOKEN
```

### Resposta

```json
{
    "ok": true,
    "ticket_id": 10,
    "placa": "ABC1D23",
    "marca": "Toyota",
    "modelo": "Corolla",
    "entrada": "2026-09-06T18:00:00-03:00",
    "saida": "2026-09-06T19:30:00-03:00",
    "valor": 20
}
```

---

# 💰 Regras de cobrança

O cálculo é realizado pela função:

```python
calcular_valor(entrada, saida, tipo)
```

### Tolerância

Se o veículo permanecer por até **5 minutos**, o valor é:

```text
R$ 0,00
```

### 🏍️ Moto

A tarifa definida atualmente é:

```text
R$ 15,00
```

### 🚗 Veículo pequeno

| Permanência    |    Valor |
| -------------- | -------: |
| Até 5 min      |  R$ 0,00 |
| Até 1 hora     | R$ 10,00 |
| Mais de 1 hora | R$ 20,00 |

### 🚙 Veículo grande

| Permanência    |    Valor |
| -------------- | -------: |
| Até 5 min      |  R$ 0,00 |
| Até 1 hora     | R$ 20,00 |
| Mais de 1 hora | R$ 30,00 |

### 🌙 Período após fechamento

Para períodos que atravessam o horário de fechamento definido no código, a aplicação considera:

```text
18:00
```

A tarifa base é:

* Pequeno: R$ 20,00
* Grande: R$ 30,00

A cada período adicional de 12 horas, a tarifa base é adicionada novamente.

---

# 📊 Relatórios

## `POST /relatorios`

Retorna informações consolidadas dos tickets.

### Header

```http
Authorization: Bearer SEU_TOKEN
```

### Filtros

```json
{
    "data_inicio": "2026-09-01",
    "data_fim": "2026-09-06",
    "tipo": "todos"
}
```

O campo `tipo` pode ser:

```text
todos
pequeno
grande
moto
```

Os filtros de data são opcionais.

### Resposta

```json
{
    "total_veiculos": 25,
    "valor_total": 450.0,
    "por_hora": [
        {
            "hora": 8,
            "total": 5
        },
        {
            "hora": 9,
            "total": 8
        }
    ],
    "por_dia": [
        {
            "dia": "2026-09-01",
            "total": 10
        },
        {
            "dia": "2026-09-02",
            "total": 15
        }
    ],
    "por_marca": [
        {
            "marca": "Toyota",
            "total": 8
        },
        {
            "marca": "Honda",
            "total": 5
        }
    ]
}
```

---

# 🔒 Autenticação

A API utiliza **JWT (JSON Web Token)**.

Após realizar o login, o cliente recebe um token:

```json
{
    "token": "..."
}
```

Esse token deve ser enviado nas rotas protegidas:

```http
Authorization: Bearer SEU_TOKEN
```

Atualmente, as rotas que utilizam autenticação são:

```text
POST /entrada
POST /saida
POST /relatorios
```

Os tickets são associados ao usuário autenticado através do campo:

```text
user_id
```

Isso permite que cada usuário consulte e gerencie seus próprios registros.

---

# 🌎 Timezone

A aplicação utiliza o fuso horário:

```text
America/Sao_Paulo
```

O horário atual é obtido através de:

```python
datetime.now(tz)
```

Isso evita depender diretamente do timezone configurado no servidor.

---

# 🌐 CORS

A aplicação está configurada atualmente para aceitar requisições de qualquer origem:

```python
allow_origins=["*"]
```

Também estão habilitados:

```text
GET
POST
PUT
DELETE
PATCH
OPTIONS
```

> ⚠️ Para produção, recomenda-se substituir `["*"]` pelos domínios reais do frontend.

---

# 📦 Dependências

O projeto utiliza o seguinte `requirements.txt`:

```txt
re
fastapi
uvicorn
psycopg2-binary
pytz
passlib
bcrypt
python-jose
```

> **Observação:** `re` faz parte da biblioteca padrão do Python e normalmente **não deve ser colocado no `requirements.txt`**.

Uma versão mais adequada seria:

```txt
fastapi
uvicorn
psycopg2-binary
pytz
passlib
bcrypt
python-jose
```

---

# 🧪 Testando com Swagger

Depois de iniciar a aplicação:

```bash
uvicorn main:app --reload
```

acesse:

```text
http://127.0.0.1:8000/docs
```

A interface Swagger permite testar todos os endpoints diretamente pelo navegador.

### Fluxo recomendado

1. Criar usuário em `/register`
2. Fazer login em `/login`
3. Copiar o `token`
4. Enviar o token nas rotas protegidas
5. Registrar entrada em `/entrada`
6. Registrar saída em `/saida`
7. Consultar informações em `/relatorios`

---

# 🚀 Deploy

Para executar em produção, evite utilizar:

```bash
uvicorn main:app --reload
```

Utilize, por exemplo:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

A variável `DATABASE_URL` deve ser configurada no ambiente de produção.

---

# ⚠️ Segurança

Antes de colocar a API em produção, recomenda-se:

* Alterar o `SECRET_KEY`
* Armazenar o segredo em variável de ambiente
* Restringir o CORS
* Remover o endpoint `/hash`
* Não retornar exceções internas diretamente ao cliente
* Validar os dados recebidos com modelos Pydantic
* Adicionar expiração aos tokens JWT
* Implementar tratamento específico para usuário já cadastrado
* Utilizar HTTPS
* Validar e normalizar placas
* Adicionar controle de acesso às operações
* Utilizar pool de conexões com PostgreSQL

Por exemplo, o segredo atualmente está definido diretamente no código:

```python
SECRET_KEY = "SUPER_SECRET_KEY_123"
```

Em produção, prefira:

```python
SECRET_KEY = os.getenv("SECRET_KEY")
```

E configure:

```text
SECRET_KEY=uma-chave-secreta-forte
```

---

# 📄 Licença

Defina aqui a licença do projeto.

Exemplo:

```text
MIT License
```

---

## 👨‍💻 Desenvolvimento

Projeto desenvolvido para gerenciamento de estacionamento utilizando uma API REST com FastAPI e PostgreSQL.
