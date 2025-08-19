from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers.chat import router as chat_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Construction RAG API",
        version="0.1.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "Construction RAG API"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    app.include_router(chat_router)
    return app


app = create_app()

