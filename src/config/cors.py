from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://admin.localhost:3000","http://sls.localhost:3000","https://admin.vowerp.co.in"],  # ✅ Allows requests from any frontend URL
        allow_credentials=True,
        allow_methods=["*"],  # ✅ Allows all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],  # ✅ Allows all headers
    )
