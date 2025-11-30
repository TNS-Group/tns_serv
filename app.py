from hashlib import sha256

from datetime import time
import enum

from flask import Flask, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from sqlalchemy import ForeignKey, Integer, LargeBinary, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Globals
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SECRET_KEY'] = sha256(b'secretKey').hexdigest()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
admin = Admin()

db.init_app(app)
admin.init_app(app)

# Models
class SerializableMixin:
    __hidden__ = []

    def to_dict(self):
        result = {}
        for col in self.__table__.columns: # pyright: ignore[reportAttributeAccessIssue]
            if col.name not in self.__hidden__:
                result[col.name] = getattr(self, col.name)
        return result


class ImageModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    teacher_id: Mapped[int] = mapped_column(ForeignKey('teacher.id'))
    data = db.Column(LargeBinary, nullable=False)
    mimetype = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class WeekDays(enum.Enum):
    Monday=0
    Tuesday=1 
    Wednesday=2
    Thursday=3 
    Friday=4


class SchoolClass(db.Model, SerializableMixin):
    __tablename__ = 'school_class'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(32))
    grade: Mapped[int] = mapped_column(db.Integer)

    def __str__(self):
        return self.name

    
class Teacher(db.Model, SerializableMixin):
    __tablename__ = 'teacher'
    __hidden__ = ['token', 'email_address']
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(db.String(64), nullable=True)

    full_name: Mapped[str] = mapped_column(db.String(32))

    email_address: Mapped[str] = mapped_column(db.String(128), unique=True)

    postfix: Mapped[str] = mapped_column(db.String(5))
    prefix: Mapped[str] = mapped_column(db.String(5))

    main_subject: Mapped[str] = mapped_column(db.String(32))


    def __str__(self):
        return f'{self.prefix} {self.full_name} {self.postfix}'


class Schedule(db.Model, SerializableMixin):
    __tablename__ = 'teacher_schedule'
    id: Mapped[int] = mapped_column(primary_key=True)

    class_id: Mapped[int] = mapped_column(ForeignKey('school_class.id'))
    teacher_id: Mapped[int] = mapped_column(ForeignKey('teacher.id'))
    subject: Mapped[str] = mapped_column(db.String(32))
 
    school_class = db.relationship("SchoolClass", backref="schedules")
    teacher = db.relationship("Teacher", backref="schedules")

    weekday: Mapped[WeekDays] = mapped_column(db.Enum(WeekDays))
    time_in: Mapped[time] = mapped_column(db.Time)
    time_out: Mapped[time] = mapped_column(db.Time)

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'teacher_id': self.teacher_id,
            'subject': self.subject,
            'weekday': self.weekday.name,
            'time_in': self.time_in.isoformat() if self.time_in else None,
            'time_out': self.time_out.isoformat() if self.time_out else None,
        }


# Other Boilerplate
class ScheduleAdmin(ModelView):
    form_columns = [
        'school_class',
        'teacher',
        'subject',
        'weekday',
        'time_in',
        'time_out'
    ]


admin.add_view(ModelView(SchoolClass, db.session))
admin.add_view(ModelView(Teacher, db.session))
admin.add_view(ModelView(Schedule, db.session))

with app.app_context():
    db.create_all()


# Events
@event.listens_for(Teacher, "after_insert")
def after_teacher_insert(mapper, connection, target):
    if target.token:
        hashed = sha256(f"{target.id}{target.token}".encode()).hexdigest()
        connection.execute(
            Teacher.__table__.update() # pyright: ignore[reportAttributeAccessIssue]
            .where(Teacher.id == target.id)
            .values(token=hashed)
        )


# Requests
@app.route('/getSchedule', methods=['GET'])
def get_schedule():
    headers = request.headers
    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401

    schedule = db.session.get(Schedule, headers.get('SCHEDULE_ID'))

    if not schedule:
        return {'error': 'Not Found'}, 404

    if schedule.teacher_id != teacher.teacher_id:
        return {'error': 'Unauthorized'}, 401

    return jsonify(schedule.to_dict())


@app.route('/getTeacherSelf', methods=['get'])
def get_teacher_self():
    headers = request.headers
    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401
    
    return jsonify(teacher.to_dict())


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    teacher = db.session.query(Teacher).filter_by(email_address=data.get('email')).scalar()

    print(data)

    if not teacher: return {'error': 'Wrong e-mail or password'}, 401
    if teacher.token != sha256(f"{teacher.id}{data.get('password')}".encode()).hexdigest():
        return {'error': 'Wrong e-mail or password'}, 401
    
    return {'token': teacher.token}

@app.route('/getSchedulesOfTeacher', methods=['GET'])
def get_schedules_of_teacher():
    teacher_id = request.args.get('teacher_id', type=int)
    print (teacher_id)
    teacher = db.session.get(Teacher, teacher_id)

    if not teacher:
        return {'error': 'Not found'}, 404

    schedules = db.session.query(Schedule).filter_by(teacher_id=teacher_id).all()
    return jsonify({'schedules': [sch.to_dict() for sch in schedules]})

@app.get('/getTeacher')
def get_teacher():
    data = request.get_json()
    teacher = db.session.query(Teacher).filter_by(email_address=data.get('id')).scalar()
    
    if not teacher:
        return {'error': 'Not Found'}, 404

    return jsonify(teacher.to_dict())

@app.get('/getUpdatedTeacherList')
def get_updated_teacher_list():
    teachers = [ t.to_dict() for t in db.session.query(Teacher).all()]
    return teachers

@app.get('/getAllClasses')
def get_all_classes():
    classes = [ c.to_dict() for c in db.session.query(SchoolClass).all()]
    return {'classes': classes}

@app.route('/updateProfile', methods=['POST'])
def update_profile():
    headers = request.headers
    data = request.get_json()
    teacher: Teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401
    teacher = db.session.get(Teacher, teacher.id) # pyright: ignore

    if 'name' in data:
        teacher.full_name = data.get('name')
    if 'prefix' in data:
        teacher.prefix = data.get('prefix')
    if 'postfix' in data:
        teacher.postfix = data.get('postfix')
    if 'subject' in data:
        teacher.main_subject = data.get('subject')

    db.session.commit()
    return {'msg': 'Okay'}, 200

# TODO: 
@app.route('/editSchedule', methods=['POST'])
def edit_schedule():
    headers = request.headers
    data = request.get_json()
    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    print(data)

    if not teacher:
        return {'error': 'Unauthorized'}, 401

    schedule = db.session.get(Schedule, data['id'])

    if not schedule:
        return {'error': 'Not Found'}, 404

    schedule.class_id = data["class_id"] # pyright: ignore
    schedule.teacher_id = teacher.id # pyright: ignore
    schedule.subject = data["subject"] # pyright: ignore
    schedule.weekday = WeekDays[data["weekday"]] # pyright: ignore
    schedule.time_in = time.fromisoformat(data["time_in"]) # pyright: ignore
    schedule.time_out = time.fromisoformat(data["time_out"]) # pyright: ignore

    db.session.commit()

    return {'id': schedule.id}, 200 # pyright: ignore

@app.route('/deleteSchedule', methods=['POST'])
def del_schedule():
    headers = request.headers
    data = request.get_json()
    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401

    schedule = db.session.get(Schedule, data['id'])
    db.session.delete(schedule)
    db.session.commit()

    return {'message': 'Deleted..'}, 200

@app.route('/addSchedule', methods=['POST'])
def add_schedule():
    headers = request.headers
    data = request.get_json()
    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401

    new_sched = Schedule()

    new_sched.class_id = data["class_id"]
    new_sched.teacher_id = teacher.id
    new_sched.subject = data["subject"]
    new_sched.weekday = WeekDays[data["weekday"]]
    new_sched.time_in = time.fromisoformat(data["time_in"])
    new_sched.time_out = time.fromisoformat(data["time_out"])

    db.session.add(new_sched)
    db.session.commit()

    return {'id': new_sched.id}, 200

# TODO: 
@app.route('/notifyTeacher', methods=['POST'])
def notify_teacher():
    return ''

@app.route('/profile/<int:teahcer_id>')
def get_profile(teacher_id):
    img = db.session.query(ImageModel).filter_by(teacher_id=teacher_id)

    if not img:
        return {'error': 'Image not found'}, 404

    return Response(img.data, mimetype=img.mimetype) # pyright: ignore

@app.route('/uploadProfilePicture', methods=['POST'])
def upload_profile():
    headers = request.headers

    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400

    teacher = db.session.query(Teacher).filter_by(token=headers.get('Authorization')).scalar()

    if not teacher:
        return {'error': 'Unauthorized'}, 401
    
    file = request.files['file']
    data = file.read()  # raw bytes

    img = ImageModel()
    
    img.teacher_id = teacher.id
    img.data = data
    img.mimetype = file.mimetype
    img.filename = file.filename

    db.session.add(img)
    db.session.commit()

    return {
        'message': 'uploaded',
        'image_id': img.id
    }

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
    # serve(app, port=8080)
