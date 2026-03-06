from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Use routers and config from the backend package
from backend.routers import designs, categories
from backend import config


def create_app():
    app = FastAPI(
        title="Broderie Designs API",
        description="API pour l'application de designs de broderie",
        version="1.0.0"
    )

    # Use CORS origins from backend/config.py (CORS_ORIGINS)
    origins = getattr(config, "CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]) 

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _sanitize_bytes(obj):
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if isinstance(obj, list):
            return [_sanitize_bytes(item) for item in obj]
        if isinstance(obj, dict):
            return {key: _sanitize_bytes(value) for key, value in obj.items()}
        return obj

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        safe_errors = _sanitize_bytes(exc.errors())
        return JSONResponse(status_code=422, content={"detail": safe_errors})

    # Include routers
    app.include_router(designs.router)
    app.include_router(categories.router)

    @app.get("/")
    def root():
        return {"message": "Bienvenue sur l'API Broderie Designs"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


# Optional for local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
