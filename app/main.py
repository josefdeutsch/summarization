from fastapi import FastAPI

app = FastAPI()


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/run-curator')
def run_curator() -> dict[str, str | list[str]]:
    return {
        'status': 'mocked',
        'message': 'run-curator is a mock response for now',
        'takeaways': [],
    }
