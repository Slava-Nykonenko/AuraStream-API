from fastapi import FastAPI
from api.movies import router as movies_router
from api.auth import router as auth_router
app = FastAPI()

api_version_prefix = "/api/v1"

app.include_router(movies_router, prefix=api_version_prefix)
app.include_router(auth_router, prefix=api_version_prefix)
