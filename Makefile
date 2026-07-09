SHELL := /bin/bash
.PHONY: help tailwind-build tailwind-watch test migrate run docker-up docker-down check

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

tailwind-build:  ## Build Tailwind CSS for production
	@echo "Make sure tailwindcss binary is installed (see README). If not found, run:"
	@echo "  curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o static/css/tailwindcss && chmod +x static/css/tailwindcss"
	@which static/css/tailwindcss 2>/dev/null && static/css/tailwindcss -i static/css/input.css -o static/css/app.css --minify || echo "tailwindcss not found at static/css/tailwindcss"

tailwind-watch:  ## Watch Tailwind CSS for dev
	@which static/css/tailwindcss 2>/dev/null && static/css/tailwindcss -i static/css/input.css -o static/css/app.css --watch || echo "tailwindcss not found at static/css/tailwindcss"

test:  ## Run tests (uses SQLite unless DATABASE_URL is set)
	python -m pytest -q --tb=short

test-v:  ## Run tests verbose
	python -m pytest --tb=long -v

migrate:  ## Apply migrations
	python manage.py migrate

run:  ## Run dev server
	python manage.py runserver

check:  ## Run Django system checks
	python manage.py check --deploy

docker-up:  ## Start Docker Compose bundle
	docker compose up -d

docker-down:  ## Stop Docker Compose bundle
	docker compose down

docker-logs:  ## Tail Docker logs
	docker compose logs -f

docker-migrate:  ## Run migrations in Docker
	docker compose exec web python manage.py migrate
