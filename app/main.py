from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import router as process_router
from app.database import Base, engine

app = FastAPI(
    title="Document Processor API",
    description="API for asynchronous text document processing",
    version="0.1.0",
)

Base.metadata.create_all(bind=engine)
app.include_router(process_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    template_file = "app/templates/index.html"
    return FileResponse(template_file)


@app.get("/ui", response_class=HTMLResponse)
def render_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
