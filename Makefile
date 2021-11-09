shell: build
	docker-compose run --service-ports --rm app bash

debug: build
	docker-compose run --service-ports --rm app poetry run python manage.py runserver 0.0.0.0:8000

build:
	docker-compose build
