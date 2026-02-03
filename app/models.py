from hashlib import sha256
from typing import List
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship
from wtforms import EmailField, PasswordField
from .database import Base
from sqladmin import ModelView
from datetime import time
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, LargeBinary, String, Time, event, select
from .enums import WeekDays, Availability
from . import globals as globs


class ImageModel(Base):
    __tablename__ = 'image_model'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey('teacher.id'),
        unique=True,
        nullable=False
    )

    teacher: Mapped["Teacher | None"] = relationship(
        "Teacher",
        back_populates="profile_picture_image",
        uselist=False
    )

    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mimetype: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)


class SchoolClass(Base):
    __tablename__ = 'school_class'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    grade: Mapped[int] = mapped_column(Integer)

    schedules: Mapped[List["Schedule"]] = relationship(back_populates='school_class')

    def __str__(self):
        return self.name

    
class Teacher(Base):
    __tablename__ = 'teacher'
    _regenerate_token = True
    id: Mapped[int] = mapped_column(primary_key=True)

    firebase_token: Mapped[str] = mapped_column(String(256), nullable=True)

    full_name: Mapped[str] = mapped_column(String(32))
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    email_address: Mapped[str] = mapped_column(String(128), unique=True)

    prefix: Mapped[str] = mapped_column(String(5), default='', nullable=True)
    postfix: Mapped[str] = mapped_column(String(5), default='', nullable=True)

    availability: Mapped[Availability] = mapped_column(Enum(Availability), default=Availability.Absent, nullable=False)

    main_subject: Mapped[str] = mapped_column(String(128), nullable=True)

    profile_picture_image: Mapped["ImageModel | None"] = relationship(
        "ImageModel",
        back_populates="teacher",
        uselist=False,
        lazy="select",
        cascade="all, delete-orphan"
    )

    schedules: Mapped[List["Schedule"]] = relationship(
        back_populates='teacher',
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f'{self.prefix} {self.full_name} {self.postfix}'

@event.listens_for(Teacher, "before_insert", propagate=True)
@event.listens_for(Teacher, "before_update", propagate=True)
def hash_password_and_generate_token(mapper, connection, target: Teacher):
    cleartext_password = target.token

    payload = {
        "event": "reload",
        "teacher_id": target.id,
    }

    # for t in globs.SSE_TABLET_CONNECTIONS.values():
    #     t.put(payload)
    
    if cleartext_password and target._regenerate_token:
        source_string = f"{target.email_address}{cleartext_password}".encode('utf-8')
        target.token = sha256(source_string).hexdigest()


class Schedule(Base):
    __tablename__ = 'teacher_schedule'
    id: Mapped[int] = mapped_column(primary_key=True)

    class_id: Mapped[int | None] = mapped_column(ForeignKey('school_class.id'), nullable=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey('teacher.id'))
    subject: Mapped[str] = mapped_column(String(32))
 
    school_class = relationship("SchoolClass", back_populates="schedules")
    teacher = relationship("Teacher", back_populates="schedules")

    weekday: Mapped[WeekDays] = mapped_column(Enum(WeekDays))
    time_in: Mapped[time] = mapped_column(Time)
    time_out: Mapped[time] = mapped_column(Time)

    is_break: Mapped[bool] = mapped_column(Boolean)


class SchoolClassAdmin(ModelView, model=SchoolClass):
    column_list = [SchoolClass.id, SchoolClass.name, SchoolClass.grade]


class TeacherAdmin(ModelView, model=Teacher):
    column_list = [Teacher.id, Teacher.email_address, Teacher.full_name, Teacher.main_subject, Teacher.token]
    form_columns = [
        Teacher.full_name,
        Teacher.email_address,
        Teacher.token,
        Teacher.postfix,
        Teacher.prefix,
        Teacher.main_subject,
    ]

    form_overrides = {
        'token': PasswordField,
        'email_address': EmailField
    }

    form_args = {
        'token': {
            'label': 'Password'
        }
    }


class ScheduleAdmin(ModelView, model=Schedule):
    column_list = [Schedule.id, Schedule.subject, Schedule.school_class, Schedule.teacher, Schedule.weekday, Schedule.time_in, Schedule.time_out] # pyright: ignore

