from contextlib import asynccontextmanager
from hashlib import sha256
from fastapi import FastAPI
from sqladmin import Admin

from .admin_auth import AdminAuth

from . import api, models, schemas
from .database import init_db, engine

import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate(".firebaseServiceKey.json")
firebase_admin.initialize_app(cred)

SESSION_SECRET_KEY = sha256(b'secret_key').hexdigest()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title = "TNS API",
    version = "0.1.0",
    lifespan = lifespan
)

admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=SESSION_SECRET_KEY))
admin.add_view(models.SchoolClassAdmin)
admin.add_view(models.ScheduleAdmin)
admin.add_view(models.TeacherAdmin)

app.include_router(api.router, tags=['API'], prefix='/api')

