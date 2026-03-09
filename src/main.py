from fastapi import FastAPI
from api.movies import router as movies_router
app = FastAPI()

api_version_prefix = "/api/v1"

app.include_router(movies_router, prefix=api_version_prefix)
