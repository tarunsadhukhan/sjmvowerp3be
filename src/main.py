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
from src.common.ctrldskAdmin.users import router as co_ctrldsk_users_router
from src.common.ctrldskAdmin.orgs import router as co_ctrldsk_orgs_router
from src.common.companyAdmin.company import router as co_company_router
from src.common.ctrldskAdmin.menuportal import router as co_ctrldsk_menu_router
from src.common.companyAdmin.branch import router as co_branch_router
from src.common.companyAdmin.dept_subdept import router as co_dept_subdept_router

from src.masters.departments import router as dept_router
from src.masters.mechineMaster import router as machine_router
from src.masters.projectMaster import router as project_router 
from src.procurement.indent import router as indent_router
from src.procurement.po import router as po_router
from src.procurement.inward import router as inward_router
from src.procurement.material_inspection import router as material_inspection_router
from src.procurement.sr import router as sr_router
from src.procurement.drcr_note import router as drcr_note_router
from src.procurement.billpass import router as billpass_router
from src.masters.party import router as party_router
from src.inventory.issue import router as issue_router

from src.masters.items import router as item_router
from src.masters.warehouse import router as warehouse_router
from src.masters.castFactor import router as costFactor_router
from src.masters.juteQuality import router as jute_quality_router
from src.masters.juteSupplier import router as jute_supplier_router
from src.juteProcurement.jutePO import router as jute_po_router
from src.juteProcurement.juteGateEntry import router as jute_gate_entry_router
from src.juteProcurement.materialInspection import router as jute_material_inspection_router
from src.juteProcurement.mr import router as jute_mr_router
from src.config.cors import add_cors_middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
# from contextlib import asynccontextmanager

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
app.include_router(co_ctrldsk_users_router, prefix="/api/ctrldskAdmin", tags=["ctrldsk-admin-users"])
app.include_router(co_ctrldsk_orgs_router, prefix="/api/ctrldskAdmin", tags=["ctrldsk-admin-orgs"])
app.include_router(co_company_router, prefix="/api/companyAdmin", tags=["company-admin-company"])
app.include_router(co_ctrldsk_menu_router, prefix="/api/ctrldskAdmin", tags=["ctrldsk-admin-menu"])
app.include_router(co_branch_router, prefix="/api/companyAdmin", tags=["company-admin-branch"])
app.include_router(co_dept_subdept_router, prefix="/api/companyAdmin", tags=["company-admin-dept-subdept"])
app.include_router(item_router, prefix="/api/itemMaster", tags=["masters-items"])

app.include_router(dept_router, prefix="/api/deptMaster", tags=["masters-departments"])
app.include_router(machine_router, prefix="/api/mechMaster", tags=["masters-machines"])
app.include_router(project_router, prefix="/api/projectMaster", tags=["masters-projects"])

app.include_router(party_router, prefix="/api/partyMaster", tags=["masters-party"])
app.include_router(warehouse_router, prefix="/api/warehouseMaster", tags=["masters-warehouse"])
app.include_router(costFactor_router, prefix="/api/costFactorMaster", tags=["masters-costFactor"])
app.include_router(jute_quality_router, prefix="/api/juteQualityMaster", tags=["masters-jute-quality"])
app.include_router(jute_supplier_router, prefix="/api/juteSupplierMaster", tags=["masters-jute-supplier"])

app.include_router(indent_router, prefix="/api/procurementIndent", tags=["procurement-indent"])
app.include_router(po_router, prefix="/api/procurementPO", tags=["procurement-po"])
app.include_router(inward_router, prefix="/api/procurementInward", tags=["procurement-inward"])
app.include_router(material_inspection_router, prefix="/api/materialInspection", tags=["procurement-material-inspection"])
app.include_router(sr_router, prefix="/api/storesReceipt", tags=["procurement-stores-receipt"])
app.include_router(drcr_note_router, prefix="/api/drcrNote", tags=["procurement-drcr-note"])
app.include_router(billpass_router, prefix="/api/billPass", tags=["procurement-bill-pass"])

# Jute Procurement routers
app.include_router(jute_po_router, prefix="/api/jutePO", tags=["jute-procurement-po"])
app.include_router(jute_gate_entry_router, prefix="/api/juteGateEntry", tags=["jute-procurement-gate-entry"])
app.include_router(jute_material_inspection_router, prefix="/api/juteMaterialInspection", tags=["jute-procurement-material-inspection"])
app.include_router(jute_mr_router, prefix="/api/juteMR", tags=["jute-procurement-mr"])

# Inventory routers
app.include_router(issue_router, prefix="/api/inventoryIssue", tags=["inventory-issue"])



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
