import logging
from fastapi import FastAPI, Request
from src.common.routers import router as common_router
from src.authorization.routers import common_router as auth_router
from src.common.companydata import router as company_router
from src.common.companyAdmin.menu import router as co_console_router
from src.common.companyAdmin.roles import router as co_roles_router
from src.common.companyAdmin.users import router as co_users_router
from src.common.portal.roles import router as co_portal_router
from src.common.portal.users import router as co_portal_users_router
from src.common.portal.menu import router as co_portal_menu_router
from src.common.portal.approval import router as co_portal_approval_router
from src.common.ctrldskAdmin.roles import router as co_ctrldsk_router
from src.config.cors import add_cors_middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager

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
app.include_router(co_console_router, prefix="/api/companyAdmin", tags=["company-admin-menu"])
app.include_router(co_roles_router, prefix="/api/companyAdmin", tags=["company-admin-roles"])
app.include_router(co_users_router, prefix="/api/companyAdmin", tags=["company-admin-users"])
app.include_router(co_portal_router, prefix="/api/admin/PortalData", tags=["PortalDataInAdmin"])
app.include_router(co_portal_users_router, prefix="/api/admin/PortalData", tags=["PortalDataInAdmin"])
app.include_router(co_portal_menu_router, prefix="/api/admin/PortalData", tags=["PortalDataInAdmin"])
app.include_router(co_portal_approval_router, prefix="/api/admin/PortalData", tags=["PortalDataInAdmin"])
app.include_router(co_ctrldsk_router, prefix="/api/ctrldskAdmin", tags=["ctrldsk-admin-roles"])


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Application is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down...")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # 👇 Startup logic
#     logger.info("Application is starting up...")
#     yield
#     # 👇 Shutdown logic
#     logger.info("Application is shutting down...")

# app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
