from fastapi import FastAPI

app = FastAPI()


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/run-curator')
def run_curator() -> dict[str, object]:
    return {
        'status': 'accepted',
        'message': 'Mock curator workflow response',
    }
