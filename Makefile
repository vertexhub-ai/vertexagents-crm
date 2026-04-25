.PHONY: dev test lint migrate

dev:
	docker-compose up -d
	python manage.py migrate --settings=config.settings.dev
	python manage.py runserver --settings=config.settings.dev

test:
	pytest accounts/tests/ -v

migrate:
	python manage.py migrate --settings=config.settings.dev

lint:
	python -m py_compile accounts/models.py accounts/permissions.py accounts/views.py
