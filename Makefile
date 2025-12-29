start:
	docker compose up --build

lint:
	uv run ruff check . --fix && ruff format .

test:
	uv run pytest