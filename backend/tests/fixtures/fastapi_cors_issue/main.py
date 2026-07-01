from fastapi import FastAPI

from routes.auth import router as auth_router

app = FastAPI(title="Demo FastAPI Auth")
app.include_router(auth_router)
