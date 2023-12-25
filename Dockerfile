FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=off \
  POETRY_VERSION=1.6.1

WORKDIR /code
COPY poetry.lock pyproject.toml /code

RUN ls -la
RUN pip install --no-cache-dir --progress-bar off "poetry==$POETRY_VERSION"

RUN poetry config virtualenvs.create false \
  && poetry install --no-cache --no-interaction --no-ansi

# docker buildx build --push --platform linux/arm64,linux/amd64 --tag artemiyjjj/python-tools -f Dockerfile .
# docker run -it artemiyjjj/python-tools /bin/sh
