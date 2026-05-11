# Curso Langflow

Ambiente local para o curso, composto por **Langflow** (plataforma de fluxos de IA) e **JupyterLab** (notebooks Python), orquestrados via Docker Compose.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) >= 24
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20 (incluso no Docker Desktop)
- `make` (opcional, mas recomendado)

## Configuração inicial

### 1. Clone o repositório

```bash
git clone <url-do-repo>
cd curso-langflow
```

### 2. Crie o arquivo de variáveis de ambiente

```bash
cp .env.example .env
```

Abra o `.env` e preencha as chaves de API:

| Variável | Descrição | Onde obter |
|---|---|---|
| `LANGFLOW_SUPERUSER_PASSWORD` | Senha do admin do Langflow | Defina livremente (padrão: `admin`) |
| `OPENAI_API_KEY` | Chave da API OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |

> `LANGFLOW_API_KEY` é gerada automaticamente — deixe em branco.

### 3. Suba o ambiente

Na **primeira execução** (faz o build da imagem do JupyterLab):

```bash
make build
```

Nas execuções seguintes:

```bash
make up
```

O stack sobe três containers em sequência:

1. `langflow` — aguarda o healthcheck passar
2. `langflow-init` — cria a API key e salva no volume compartilhado
3. `jupyter` — inicia o JupyterLab

## Acessando os serviços

| Serviço | URL |
|---|---|
| Langflow | <http://localhost:7860> |
| JupyterLab | <http://localhost:8888> |

Login no Langflow: usuário `admin` + a senha definida em `LANGFLOW_SUPERUSER_PASSWORD`.  
O JupyterLab não exige senha.

## Recuperando a API key do Langflow

```bash
make api-key
```

O valor gerado também fica disponível em `/config/langflow.env` dentro do volume `langflow-config`, montado como leitura no JupyterLab em `/config/langflow.env`.

## Comandos úteis

```bash
make up            # Sobe todos os containers em background
make down          # Para e remove os containers
make restart       # Reinicia os containers
make logs          # Segue os logs de todos os serviços
make logs-langflow # Segue apenas os logs do Langflow
make logs-jupyter  # Segue apenas os logs do JupyterLab
make ps            # Lista os containers e seus status
make clean         # Remove containers, volumes e dados locais (destrutivo)
```

## Estrutura do projeto

```
.
├── data/          # Banco SQLite e arquivos de configuração do Langflow (persistido)
├── docs/          # Documentação do curso
├── flows/         # Flows do Langflow carregados automaticamente na inicialização
├── notebooks/     # Notebooks do JupyterLab
├── scripts/       # Scripts de inicialização (criação da API key)
├── .env.example   # Template de variáveis de ambiente
├── docker-compose.yml
├── Dockerfile.jupyter
└── Makefile
```

## Solução de problemas

**Langflow demora para iniciar**  
É normal — o healthcheck aguarda até 90 s. Monitore com `make logs-langflow`.

**JupyterLab não sobe**  
O JupyterLab depende do `langflow-init` ter concluído com sucesso. Verifique:

```bash
docker compose logs langflow-init
```

**API key não encontrada**  
Execute `make build` novamente para recriar o container `langflow-init`.

**Resetar tudo do zero**  
```bash
make clean
make build
```
