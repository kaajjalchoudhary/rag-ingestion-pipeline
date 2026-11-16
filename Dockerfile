# ragprep as a container: index and search a folder of documents.
#   docker run --rm -v "$PWD:/data" ghcr.io/kaajjalchoudhary/ragprep ingest docs --db index.sqlite
FROM python:3.12-slim

LABEL org.opencontainers.image.description="Clean, chunk, deduplicate and incrementally index documents for RAG"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY ragprep ./ragprep
RUN pip install --no-cache-dir . && useradd --create-home ragprep

USER ragprep
WORKDIR /data
ENTRYPOINT ["ragprep"]
CMD ["--help"]
