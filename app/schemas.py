import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from .enums import WeekDays, Availability

class Connection(BaseModel):
    user_id: int
    message: str
    data: Optional[Dict[int, Any]] = None

class ImageModelBaseSchema(BaseModel):
    id: int | None = None

    data: bytes
    mimetype: str
    filename: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class SchoolClassBaseSchema(BaseModel):
    id: int | None = None

    name: str
    grade: int

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class TeacherBaseSchema(BaseModel):
    full_name: str | None = None

    postfix: str | None = None
    prefix: str | None = None

    main_subject: str | None = None

    availability: Availability | None = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class TeacherResponse(TeacherBaseSchema):
    id: int

class TeacherUpdate(TeacherBaseSchema):
    email_address: str | None = None
    new_password: str | None  = None
    old_password: str | None  = None

class TeacherLoginResponse(TeacherResponse):
    token: str
    email_address: str

class ScheduleBaseSchema(BaseModel):
    class_id: int
    teacher_id: int

    subject: str
    weekday: WeekDays
    time_in: datetime.time
    time_out: datetime.time

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class ScheduleResponse(ScheduleBaseSchema):
    id: int

class ScheduleCreate(BaseModel):
    class_id: int

    subject: str
    weekday: WeekDays
    time_in: datetime.time
    time_out: datetime.time

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class ScheduleUpdate(BaseModel):
    id: int

    class_id: int

    subject: str
    weekday: WeekDays
    time_in: datetime.time
    time_out: datetime.time

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
