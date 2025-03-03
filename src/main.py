from fastapi import FastAPI, Request
from src.common.routers import router as common_router  # ✅ Absolute import
from src.hrms.routers import router as hrms_router  # ✅ Absolute import
from src.common.master import router as master_router  # ✅ Absolute import
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

app = FastAPI(title="Vowerp3b API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allows requests from any frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allows all headers
)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print(f"Global API Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


app.include_router(common_router, prefix="/api/common", tags=["Common"])
app.include_router(hrms_router, prefix="/api/hrms", tags=["HRMS"])
app.include_router(master_router, prefix="/api/master", tags=["Master"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
