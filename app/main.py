from fastapi import FastAPI
from api import router

app = FastAPI(title="Map Matching API")
app.include_router(router)
