debug: build
	docker-compose run --service-ports --rm app

shell: build
	docker-compose run --service-ports --rm app bash

build:
	docker-compose build

logs:
	docker-compose logs --tail 30 -f

### To run from container ###

test:
	coverage run --source=. manage.py test
	coverage report -m

# Tests without coverage
fasttest:
	python manage.py test --parallel