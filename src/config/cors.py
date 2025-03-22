from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # ✅ Allows requests from any frontend URL
        allow_credentials=True,
        allow_methods=["*"],  # ✅ Allows all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],  # ✅ Allows all headers
    )
