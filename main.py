from fastapi import FastAPI

from controllers.file_controller import file_router

app = FastAPI()

app.include_router(file_router, prefix="/file")


