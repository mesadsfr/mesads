FROM python

RUN pip install \
  uwsgi \
  poetry

RUN useradd -m mesads
USER mesads

# Improve docker cache and install dependencies before copying code.
WORKDIR /app
COPY pyproject.toml poetry.lock /app
RUN poetry install

COPY . /app

ENTRYPOINT ["poetry", "run"]

# We can't use the syntax CMD [...] because we need subshells to provide variables.
# -M: start worker process
# -p: number of workers
# -R: restart worker after N requests
CMD uwsgi -H \$\(VIRTUAL_ENV\) --http :8000 --module mesads.wsgi -M -p $(nproc) -R 100
