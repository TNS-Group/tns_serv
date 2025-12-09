import asyncio

import json

from hashlib import sha256
from typing import Annotated, List
from firebase_admin import messaging

from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from . import schemas, models, globals
from .database import get_async_session

from fastapi import APIRouter, Depends, File, HTTPException, Header, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# Tested
@router.get(
    '/schedule',
    status_code=status.HTTP_200_OK,
    response_model=schemas.ScheduleResponse
)
async def get_schedule(
    schedule_id: int,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    schedule = await db.get(models.Schedule, schedule_id)

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return schedule


# Tested
@router.post(
    '/schedule',
    status_code=status.HTTP_200_OK,
)
async def create_schedule(
    data: schemas.ScheduleCreate,
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    schedule = models.Schedule(
        **data.model_dump(),
        teacher_id = teacher.id
    )

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return {'id': schedule.id}


# Tested
@router.options(
    '/schedule',
    status_code=status.HTTP_200_OK,
)
async def edit_schedule(
    data: schemas.ScheduleUpdate,
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    schedule = await db.get(models.Schedule, data.id)

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if schedule.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    schedule.class_id = data.class_id
    schedule.subject  = data.subject 
    schedule.weekday  = data.weekday 
    schedule.time_in  = data.time_in 
    schedule.time_out = data.time_out

    await db.commit()
    await db.refresh(schedule)

    return {'id': schedule.id}


# Tested
@router.delete(
    '/schedule',
    status_code=status.HTTP_200_OK,
)
async def delete_schedule(
    schedule_id: int,
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    schedule = await db.get(models.Schedule, schedule_id)

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if schedule.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    await db.delete(schedule)
    await db.commit()

    return {'msg': 'Deleted'}


# Tested
@router.get(
    '/teacherSchedules',
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.ScheduleResponse]
)
async def get_teacher_schedules(
    teacher_id: int,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    teacher = await db.get(models.Teacher, teacher_id)

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    stmt = select(models.Schedule).where(models.Schedule.teacher_id == teacher_id)
    schedules = (await db.scalars(stmt)).all()

    if not schedules:
        return []

    return schedules


# Tested
@router.get(
    '/self', 
    status_code=status.HTTP_200_OK,
    response_model=schemas.TeacherResponse,
)
async def get_teacher_self(
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return teacher


# Tested 
@router.get(
    '/teacher', 
    status_code=status.HTTP_200_OK,
    response_model=schemas.TeacherResponse,
)
async def get_teacher(
    teacher_id: int,
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    teacher = await db.get(models.Teacher, teacher_id)

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return teacher


# Tested
@router.get(
    '/teacherList', 
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.TeacherResponse]
)
async def get_teacher_list(
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    result = await db.execute(select(models.Teacher))
    teachers = result.scalars()

    return teachers.all()


@router.get(
    '/classesList', 
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.SchoolClassBaseSchema]
)
async def get_classes_list(
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    result = await db.execute(select(models.SchoolClass))
    classes = result.scalars()

    return classes.all()


# Tested
@router.options(
    '/profile', 
    status_code=status.HTTP_200_OK,
)
async def update_profile(
    data: schemas.TeacherUpdate,
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    teacher._regenerate_token = False
    return_token = None

    old_pw_hash = sha256(f'{teacher.id}{data.old_password}'.encode('utf-8')).hexdigest()
    if data.new_password and data.old_password and old_pw_hash == teacher.token:
        teacher.token = return_token = sha256(f'{teacher.id}{data.new_password}'.encode('utf-8')).hexdigest()
    elif data.new_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    teacher.full_name = data.full_name or teacher.full_name
    teacher.postfix = data.postfix or teacher.postfix
    teacher.prefix = data.prefix or teacher.prefix
    teacher.main_subject = data.main_subject or teacher.main_subject
    teacher.email_address = data.email_address or teacher.email_address

    await db.commit()
    await db.refresh(teacher)

    return {
        'id': teacher.id, 
        'token': return_token 
    }


# Tested
@router.post(
    '/login',
    status_code=status.HTTP_200_OK,
    response_model=schemas.TeacherLoginResponse
)
async def login(
    email: str,
    password: str,
    firebase_token: str | None,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    print(email)
    print(password)
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.email_address == email)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Email or password is incorrect')

    testhash = sha256(f'{teacher.id}{password}'.encode('utf-8')).hexdigest()
    print(testhash)

    if teacher.token != testhash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Email or password is incorrect')

    if not teacher.firebase_token and firebase_token:
        teacher.firebase_token = firebase_token;
        await db.commit()
        await db.refresh(teacher)

    return teacher


# Tested
@router.post(
    '/uploadPicture',
    status_code=status.HTTP_200_OK,
)
async def upload_profile_picture(
    token: Annotated[str, Header(alias='Authorization')],
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    if not file.content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file provided.")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed.")

    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    image = (await db.scalars(
        select(models.ImageModel).where(models.ImageModel.teacher_id == teacher.id)
    )).first()

    if not image:
        image = models.ImageModel(
            teacher_id = teacher.id,
            data = await file.read(),
            mimetype = file.content_type,
            filename = str(teacher.id)
        )
        db.add(image)

    else:
        image.data = await file.read()
        image.mimetype = file.content_type
        image.filename = str(teacher.id)

    await db.commit()
    await db.refresh(image)

    return {'id': image.id}


# Tested
@router.get(
    '/profilePicture/{teacher_id}',
    status_code=status.HTTP_200_OK
)
async def get_profile_picture(
    teacher_id: int,
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    stmt = (
        select(models.Teacher)
        .where(models.Teacher.id == teacher_id)
        .options(selectinload(models.Teacher.profile_picture_image)) 
    )

    result = await db.execute(stmt)
    teacher = result.scalars().first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not teacher.profile_picture_image:
        return None

    return Response(
        content = teacher.profile_picture_image.data,
        media_type = teacher.profile_picture_image.mimetype
    )


# Tested
@router.post(
    "/notify",
    status_code=status.HTTP_200_OK
)
async def notify_teacher(
    teacher_id: int,
    tablet_session: str,
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    if not tablet_session in globals.SSE_TABLET_CONNECTIONS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    teacher = await db.get(models.Teacher, teacher_id)

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    payload = {
        "event": "notify",
        "tablet_session": tablet_session
    }

    if teacher.id in globals.SSE_TEACHER_CONNECTIONS:
        await globals.SSE_TEACHER_CONNECTIONS[teacher.id].put(payload)
        return {"status": "success", "method": "SSE"}

    if teacher.firebase_token:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Kiosk Notification",
                    body="Someone is looking for you",
                ),
                data={
                    "event": "notify",
                    "tablet_session": tablet_session,
                },
                token=teacher.firebase_token,
            )
            response = await asyncio.to_thread(messaging.send, message)
            return {"status": "success", "method": "FCM", "message_id": response}
        except Exception as e:
            print(f"FCM Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to send FCM notification"
            )

    return {"status": "failed", "reason": "No active connection or FCM token found"}


# Tested
@router.post(
    '/respond'
)
async def teacher_send_response(
    message: str,
    tablet_session: str,
    token: Annotated[str, Header(alias='Authorization')],
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = {
        "event": "response",
        "message": message,
        "teacher_id": teacher.id,
    }

    if tablet_session in globals.SSE_TABLET_CONNECTIONS:
        await globals.SSE_TABLET_CONNECTIONS[tablet_session].put(payload)
        return {"status": "success", "method": "SSE"}

    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# Tested
@router.get(
    "/eventsTablet"
)
async def tablet_events(
    request: Request
):
    assert request.client

    if request.client.host in globals.SSE_TABLET_CONNECTIONS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    tablet_session = "TABSESS_" + sha256(request.client.host.encode('utf-8')).hexdigest()

    queue = asyncio.Queue()
    globals.SSE_TABLET_CONNECTIONS[
        tablet_session
    ] = queue

    async def event_generator():
        assert request.client

        try:
            token_sse = json.dumps({
                'token': tablet_session
            })
            yield f"data: {token_sse}\n\n"
            while True:
                try:
                    message_data = await asyncio.wait_for(queue.get(), timeout=20)

                    sse_message = f"data: {json.dumps(message_data)}\n\n"
                    yield sse_message
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

                if await request.is_disconnected():
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if request.client.host in globals.SSE_TABLET_CONNECTIONS:
                del globals.SSE_TABLET_CONNECTIONS[
                    sha256(request.client.host.encode('utf-8')).hexdigest()
                ]
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# Tested
@router.get(
    "/eventsTeacher"
)
async def teacher_events(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_async_session)]
):
    teacher = (await db.scalars(
        select(models.Teacher).where(models.Teacher.token == token)
    )).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    queue = asyncio.Queue()
    globals.SSE_TEACHER_CONNECTIONS[teacher.id] = queue

    async def event_generator():
        try:
            while True:
                try:
                    message_data = await asyncio.wait_for(queue.get(), timeout=20)

                    sse_message = f"data: {json.dumps(message_data)}\n\n"
                    yield sse_message
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

                if await request.is_disconnected():
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if teacher.id in globals.SSE_TEACHER_CONNECTIONS:
                del globals.SSE_TEACHER_CONNECTIONS[teacher.id]
                print(f"User {teacher} disconnected. Active connections: {len(globals.SSE_TEACHER_CONNECTIONS)}")
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
