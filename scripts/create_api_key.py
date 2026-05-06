"""
Roda uma única vez após o Langflow estar saudável.
Cria uma API key e salva em /config/langflow.env.
Se o arquivo já existir (volume persistente), pula a criação.
"""
import os
import sys
import time
import requests

LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://langflow:7860")
SUPERUSER    = os.environ.get("LANGFLOW_SUPERUSER", "admin")
PASSWORD     = os.environ.get("LANGFLOW_SUPERUSER_PASSWORD", "admin")
CONFIG_FILE  = "/config/langflow.env"

if os.path.exists(CONFIG_FILE):
    print(f"API key já existe em {CONFIG_FILE} — nada a fazer.")
    sys.exit(0)

# Aguarda Langflow aceitar requisições (healthcheck já passou, mas a API pode demorar um pouco mais)
for attempt in range(10):
    try:
        resp = requests.get(f"{LANGFLOW_URL}/api/v1/auto_login", timeout=5)
        if resp.status_code < 500:
            break
    except requests.exceptions.ConnectionError:
        pass
    print(f"Aguardando API do Langflow... tentativa {attempt + 1}/10")
    time.sleep(3)

# Autenticar: tenta auto-login primeiro (LANGFLOW_AUTO_LOGIN=true), senão usa credenciais
resp = requests.get(f"{LANGFLOW_URL}/api/v1/auto_login", timeout=10)
if resp.status_code == 200 and "access_token" in resp.json():
    token = resp.json()["access_token"]
    print("Login OK via auto-login.")
else:
    resp = requests.post(
        f"{LANGFLOW_URL}/api/v1/login",
        data={"username": SUPERUSER, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print("Login OK via credenciais.")

# Criar API key
resp = requests.post(
    f"{LANGFLOW_URL}/api/v1/api_key/",
    json={"name": "default"},
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)
resp.raise_for_status()
api_key = resp.json()["api_key"]

# Persistir no volume compartilhado
os.makedirs("/config", exist_ok=True)
with open(CONFIG_FILE, "w") as f:
    f.write(f"LANGFLOW_API_KEY={api_key}\n")
    f.write(f"LANGFLOW_URL={LANGFLOW_URL}\n")

print(f"API key criada: {api_key}")
print(f"Salva em {CONFIG_FILE}")
