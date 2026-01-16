from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from hashlib import sha256
from fastapi import FastAPI
from sqladmin import Admin

from .admin_auth import AdminAuth

from . import api, models, schemas
from .database import init_db, engine

from . import globals

import firebase_admin
from firebase_admin import credentials

from fastapi_utilities import repeat_every


cred = credentials.Certificate(".firebaseServiceKey.json")
firebase_admin.initialize_app(cred)

SESSION_SECRET_KEY = sha256(b'secret_key').hexdigest()

async def repeat_task():
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler = AsyncIOScheduler(timezone=f'Asia/Manila')
    scheduler.add_job(func=repeat_task, trigger='interval', seconds=1)
    scheduler.start()

    yield

app = FastAPI(
    title = "TNS API",
    version = "0.1.0",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=SESSION_SECRET_KEY))
admin.add_view(models.SchoolClassAdmin)
admin.add_view(models.ScheduleAdmin)
admin.add_view(models.TeacherAdmin)

app.include_router(api.router, tags=['API'], prefix='/api')
