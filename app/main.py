import asyncio
from datetime import datetime, timedelta
from firebase_admin import messaging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from hashlib import sha256
from fastapi import FastAPI, HTTPException, status
from sqladmin import Admin
from sqlalchemy import select

from app.enums import Availability, WeekDays
from app.utils import verify_fcm_token

from .admin_auth import AdminAuth

from . import api, models, schemas
from .database import AsyncSessionLocal, get_async_session, init_db, engine

from . import globals

import firebase_admin
from firebase_admin import credentials

scheduler = AsyncIOScheduler(timezone='UTC')

cred = credentials.Certificate(".firebaseServiceKey.json")
firebase_admin.initialize_app(cred)

SESSION_SECRET_KEY = sha256(b'secret_key').hexdigest()

async def schedule_job():
    async with AsyncSessionLocal() as session:
        now = datetime.now()

        str_week_map = {
            "SUNDAY": -1,
            "MONDAY": WeekDays.Monday,
            "TUESDAY": WeekDays.Tuesday,
            "WEDNESDAY": WeekDays.Wednesday,
            "THURSDAY": WeekDays.Thursday,
            "FRIDAY": WeekDays.Friday,
            "SATURDAY": -1 
        }

        current_weekday = now.strftime('%A').upper() 
        current_time = now.time().replace(second=0, microsecond=0)
        five_mins_from_now = (datetime.combine(now, current_time) + timedelta(minutes=5)).time()

        if current_weekday == "SATURDAY" or current_weekday == "SUNDAY":
            return

        query_now = await session.execute(select(models.Schedule).where(models.Schedule.time_in == current_time, models.Schedule.weekday == str_week_map[current_weekday]))
        query_5mfn = await session.execute(select(models.Schedule).where(models.Schedule.time_in == five_mins_from_now, models.Schedule.weekday == str_week_map[current_weekday]))
        query_endclass = await session.execute(select(models.Schedule).where(models.Schedule.time_out == current_time, models.Schedule.weekday == str_week_map[current_weekday]))

        print(f"\n\n\n\n\n{current_time}\n\n\n\n\n")

        for s in query_endclass.scalars().all():
            teacher = await session.get(models.Teacher, s.teacher_id)
            assert teacher

            teacher._regenerate_token = False

            if teacher.availability == Availability.InClass:
                teacher.availability = Availability.Available
                await session.refresh(teacher)

                payloadTeacher = {
                    "event": "switchAvailability",
                    "self.availability": Availability.Available.value,
                    "availability": Availability.Available.value
                }

                payloadKiosk = {
                    "event": "reload",
                    "teacher_id": teacher.id,
                }

                for t in globals.SSE_TABLET_CONNECTIONS.values():
                    await t.put(payloadKiosk)

                if teacher.id in globals.SSE_TEACHER_CONNECTIONS:
                    await globals.SSE_TEACHER_CONNECTIONS[teacher.id].put(payloadTeacher)

        for s in query_now.scalars().all():
            teacher = await session.get(models.Teacher, s.teacher_id)
            assert teacher

            teacher._regenerate_token = False

            if teacher.availability != Availability.Absent:
                teacher.availability = Availability.DoNotDisturb if s.is_break else Availability.InClass
                await session.refresh(teacher)

                payloadTeacher = {
                    "event": "switchAvailability",
                    "self.availability": teacher.availability.value,
                    "availability": teacher.availability.value
                }

                payloadKiosk = {
                    "event": "reload",
                    "teacher_id": teacher.id,
                }

                for t in globals.SSE_TABLET_CONNECTIONS.values():
                    await t.put(payloadKiosk)

                if teacher.id in globals.SSE_TEACHER_CONNECTIONS:
                    await globals.SSE_TEACHER_CONNECTIONS[teacher.id].put(payloadTeacher)

        for s in query_5mfn.scalars().all():
            teacher = await session.get(models.Teacher, s.teacher_id)
            class_ = await session.get(models.SchoolClass, s.class_id)
            assert teacher

            if not class_:
                continue

            if teacher.firebase_token and teacher.availability != Availability.Absent:
                print("Firebase Token Validation: ", await verify_fcm_token(teacher.firebase_token))
                try:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title="Class in 5 minutes!",
                            body=f"You have a subject ({s.subject}) in {class_.name}. You have 5 minutes to prepare.",
                        ),
                        token=teacher.firebase_token,
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                title="Class in 5 minutes!",
                                body=f"You have a subject ({s.subject}) in {class_.name}. You have 5 minutes to prepare.",
                                channel_id="critical_alerts",
                                sound="alert_sound",
                            ),
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    sound=messaging.CriticalSound(
                                        name="alert_sound.caf", 
                                        critical=True, 
                                        volume=1.0
                                    ),
                                    category="RESPOND_CATEGORY", 
                                ),
                            ),
                        ),
                    )
                    
                    response = await asyncio.to_thread(messaging.send, message)
                    print(response)
                except Exception as e:
                    print(f"FCM Error: {e}")
                    print(f"Token: {teacher.firebase_token}")

        await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler.start()
    scheduler.add_job(
        func=schedule_job, 
        trigger=IntervalTrigger(minutes=1, start_date=datetime.now()),
        id="main_sync_task",
        replace_existing=True
    )

    yield
    
    scheduler.shutdown()

app = FastAPI(
    title = "TNS API",
    version = "0.1.0",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=['*'],
    allow_methods=["*"],
    allow_headers=["*"],
)

admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=SESSION_SECRET_KEY))
admin.add_view(models.SchoolClassAdmin)
admin.add_view(models.ScheduleAdmin)
admin.add_view(models.TeacherAdmin)

app.include_router(api.router, tags=['API'], prefix='/api')

