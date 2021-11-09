build:
	docker-compose build

shell: build
	docker-compose run --service-ports --rm app bash

debug: build
	docker-compose run --service-ports --rm app python manage.py runserver 0.0.0.0:8000

logs:
	docker-compose logs --tail 30 -f
