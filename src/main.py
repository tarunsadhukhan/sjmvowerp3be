import logging
from fastapi import FastAPI, Request
from src.common.routers import router as common_router
from src.authorization.routers import common_router as auth_router
from src.common.companydata import router as company_router
from src.common.companyAdmin.menu import router as co_console_router
from src.config.cors import add_cors_middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Vowerp3b API")

# ✅ Add this to trust NGINX proxy headers (like X-Forwarded-Proto)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Add CORS middleware
add_cors_middleware(app)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print(f"Global API Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

print ('mama')
app.include_router(common_router, prefix="/api/common", tags=["Common"])
app.include_router(auth_router, prefix="/api/authRoutes", tags=["Auth"])
app.include_router(company_router, prefix="/api/companyRoutes", tags=["company"])
app.include_router(co_console_router, prefix="/api/companyAdmin", tags=["companyAdmin"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Application is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
