FROM python:3.12-slim

WORKDIR /operator

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir uv && \
    uv pip install --system kopf kubernetes pydantic pyyaml

USER 1000:1000

ENTRYPOINT ["kopf", "run", "--module=lrm_operator", "--all-namespaces"]
