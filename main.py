from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pathlib import Path
import logging

# Imports absolus au lieu d'imports relatifs
from routers import designs, categories, auth, users, downloads, packs, orders, pack_orders, features, payments, contact
import config
from database import create_all_tables

logger = logging.getLogger("uvicorn.error")


def create_app():
    app = FastAPI(
        title="Broderie Designs API",
        description="API pour l'application de designs de broderie",
        version="1.0.0"
    )

    # Utiliser CORS origins depuis backend/config.py (CORS_ORIGINS)
    origins = getattr(config, "CORS_ORIGINS", [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _sanitize_validation_errors(obj):
        """Rend les erreurs Pydantic JSON-serialisables (bytes, ValueError dans ctx, etc.)."""
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if isinstance(obj, list):
            return [_sanitize_validation_errors(item) for item in obj]
        if isinstance(obj, dict):
            return {key: _sanitize_validation_errors(value) for key, value in obj.items()}
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        return str(obj)  # Exception, autre objet -> chaîne pour JSON

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        safe_errors = _sanitize_validation_errors(exc.errors())
        return JSONResponse(status_code=422, content={"detail": safe_errors})

    # Erreurs de connexion / base indisponible → 503 (ex. Railway sans MYSQL_URL)
    from sqlalchemy.exc import OperationalError

    @app.exception_handler(OperationalError)
    async def db_operational_handler(request: Request, exc: Exception):
        logger.warning("Database operational error: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "database_unavailable", "message": "Service temporairement indisponible. Vérifiez la connexion à la base de données."},
        )

    uploads_dir = Path(__file__).resolve().parent / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "designs").mkdir(parents=True, exist_ok=True)
    (uploads_dir / "designs" / "files").mkdir(parents=True, exist_ok=True)
    (uploads_dir / "categories").mkdir(parents=True, exist_ok=True)
    (uploads_dir / "packs").mkdir(parents=True, exist_ok=True)
    (uploads_dir / "orders").mkdir(parents=True, exist_ok=True)
    (uploads_dir / "pack_orders").mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.on_event("startup")
    def on_startup():
        try:
            create_all_tables()
            logger.info("Base de données connectée et tables prêtes.")
        except Exception as e:
            logger.warning(
                "Base de données indisponible au démarrage: %s. Vérifiez MYSQL_URL / MYSQL_PUBLIC_URL sur Railway.", e
            )

    # Inclure les routers
    app.include_router(designs.router)
    app.include_router(categories.router)
    app.include_router(categories.router_metadata)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(downloads.router)
    app.include_router(packs.router)
    app.include_router(pack_orders.router)
    app.include_router(features.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    app.include_router(contact.router)

    @app.get("/")
    def root():
        return {"message": "Bienvenue sur l'API Broderie Designs"}

    @app.get("/payment/success")
    def payment_success(request: Request):
        """Après paiement réussi : design_id → /designs/{id}/download, sinon order_id → /downloads?order_id=..."""
        base = getattr(config, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        design_id = request.query_params.get("design_id")
        if design_id:
            return RedirectResponse(url=f"{base}/designs/{design_id}/download", status_code=302)
        return RedirectResponse(url=f"{base}/downloads?{request.url.query}", status_code=302)

    @app.get("/payment/cancel")
    def payment_cancel(request: Request):
        """Redirige vers le frontend après annulation."""
        base = getattr(config, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        return RedirectResponse(url=f"{base}/payment/cancel?{request.url.query}", status_code=302)

    @app.get("/health")
    def health(request: Request):
        from sqlalchemy import text
        from database import engine
        status = "ok"
        db_ok = None
        if request.query_params.get("db"):
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_ok = True
            except Exception:
                db_ok = False
                status = "db_unavailable"
        return {"status": status, "database": db_ok}

    return app


app = create_app()


# Démarrage local ou via "python main.py" (Railway peut utiliser PORT)
if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=(os.getenv("ENV") != "production"))
    