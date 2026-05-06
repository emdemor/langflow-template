.PHONY: up down build restart logs ps clean api-key

up:
	docker compose up -d

build:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-langflow:
	docker compose logs -f langflow

logs-jupyter:
	docker compose logs -f jupyter

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans
	rm -rf ./data/*

api-key:
	docker run --rm -v curso-langflow_langflow-config:/config alpine cat /config/langflow.env 2>/dev/null || echo "API key ainda não gerada. Execute 'make build' primeiro."
