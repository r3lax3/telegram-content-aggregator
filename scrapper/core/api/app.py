from fastapi import FastAPI

from .endpoints import router


app = FastAPI(title="Scrapper API")
app.include_router(router)
