.PHONY: dev test lint lint-fix migrate makemigrations shell build seed createsuperuser

dev:
	docker compose up

build:
	docker compose build

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

seed:
	python manage.py seed_demo

createsuperuser:
	python manage.py createsuperuser

test:
	pytest

lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check --fix .
	ruff format .
