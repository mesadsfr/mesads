debug: build
	docker-compose run --service-ports --rm app

shell: build
	docker-compose run --service-ports --rm app bash

build:
	docker-compose build

logs:
	docker-compose logs --tail 30 -f

# Run in production mode locally, to test uWSGI
run-local-as-prod:
	docker build -t mesads .
	docker run --rm -ti \
		--network mesads_default \
		-e DEBUG=false \
		-e ALLOWED_HOSTS=* \
		-e SECRET_KEY=f981nfwnefnaipofnioadnsfipn198 \
		-e AWS_S3_ENDPOINT_URL=http://invalids3 \
		-e AWS_S3_ACCESS_KEY_ID=invalid \
		-e AWS_S3_SECRET_ACCESS_KEY=invalid \
		-e AWS_STORAGE_BUCKET_NAME=invalids3bucket \
		-p 9401:8000 \
		mesads

### To run from container ###

test:
	flake8 mesads
	coverage run --source=. manage.py test
	coverage report -m

# Tests without coverage
fasttest:
	pytest --testmon -v -x -s