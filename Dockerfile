#
# Javascript builder for static files
#
FROM node:20 AS node-builder

WORKDIR /app
COPY package.json package-lock.json /app/

RUN npm install

#
# Python builder
#
FROM python:3.11 AS python-builder

RUN pip install \
  poetry

RUN poetry config virtualenvs.path /venv

# Improve docker cache and install dependencies before copying code.
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

#
# Local development
#
FROM python-builder AS local

# nodejs is required by mjml
RUN apt-get update && apt-get install -y \
  nodejs

RUN pip install \
  uwsgi

COPY --from=node-builder /app/node_modules /app/

ENTRYPOINT ["poetry", "run"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

#
# Production runner
#
FROM python:3.11

# nodejs is required by mjml
RUN apt-get update && apt-get install -y \
  nodejs \
  npm

RUN pip install \
  poetry \
  uwsgi

WORKDIR /app

RUN poetry config virtualenvs.path /venv

COPY . /app/
COPY --from=node-builder /app/node_modules /app/node_modules
COPY --from=python-builder /venv /venv

RUN npm run build
RUN poetry run python manage.py collectstatic

EXPOSE 8000

ENTRYPOINT ["poetry", "run"]

# We can't use the syntax CMD [...] because we need subshells to provide variables.
# --enable-threads: required for sentry
# -M: start worker process
# -p: number of workers
# -R: restart worker after N requests
# --limit-post: allow to upload files up to 10MB
# --http-manage-expect: to upload large files, cURL first sends a 100-continue request which is not handled by default by uWSGI, see https://github.com/unbit/uwsgi/issues/2129
# --ignore-sigpipe, --ignore-write-errors, --disable-write-exceptions: don't report WriteError to sentry when client disconnects before the response is sent
# --cron: every hour, call python manage.py runcrons
CMD python manage.py makemigrations && python manage.py migrate && \
  uwsgi --enable-threads -H \$\(VIRTUAL_ENV\) \
  --http :8000 \
  --module mesads.wsgi \
  -M -p $(nproc) \
  -R 100 \
  -b 32768 \
  --static-map /static=/app/static \
  --limit-post=24000000 \
  --http-manage-expect \
  --ignore-sigpipe --ignore-write-errors --disable-write-exception \
  --cron='0 -1 -1 -1 -1 poetry run python /app/manage.py runcrons'
