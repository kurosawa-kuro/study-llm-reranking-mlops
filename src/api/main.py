from fastapi import FastAPI

from src.api.routes.feedback import router as feedback_router
from src.api.routes.search import router as search_router

app = FastAPI(title="Real Estate Search API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(search_router)
app.include_router(feedback_router)
