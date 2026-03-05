# Summarization API

Minimal FastAPI service with:
- `GET /health`
- `POST /run-curator`

## Run with Docker

Build the image:

```bash
docker build -t summarization-api .
```

Run the container:

```bash
docker run --rm -p 8000:8000 summarization-api
```

The API will be available at `http://localhost:8000`.
