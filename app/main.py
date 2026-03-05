from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class RunCuratorRequest(BaseModel):
    text: str
    takeaway_count: int = Field(gt=0)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/run-curator')
def run_curator(payload: RunCuratorRequest) -> dict[str, object]:
    return {
        'status': 'received',
        'takeaway_count': payload.takeaway_count,
    }
