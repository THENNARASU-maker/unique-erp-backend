from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 1. Roles Model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# 2. Users Model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(50), primary_key=True) # ID / Username
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

# 3. Departments Model
class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    hod_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=True)
    ahod_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=True)

    hod = db.relationship('User', foreign_keys=[hod_id], backref=db.backref('hod_departments', lazy=True))
    ahod = db.relationship('User', foreign_keys=[ahod_id], backref=db.backref('ahod_departments', lazy=True))

# 4. Courses Model
class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # e.g. "B.Sc. Computer Science", "BCA"
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    department = db.relationship('Department', backref=db.backref('courses', lazy=True))

# 5. Classes Model (Belongs to a Course)
class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # e.g. "CS-A", "BCA-I"
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    course = db.relationship('Course', backref=db.backref('classes', lazy=True))
    department = db.relationship('Department', backref=db.backref('classes', lazy=True))

# 6. Subjects Model
class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'class_id', name='_subject_class_uc'),)

    class_ = db.relationship('Class', backref=db.backref('subjects', lazy=True))
    department = db.relationship('Department', backref=db.backref('subjects', lazy=True))

# 7. Staff Model
class Staff(db.Model):
    __tablename__ = 'staff'
    staff_id = db.Column(db.String(50), db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Active')
    photo_url = db.Column(db.Text)

    department = db.relationship('Department', backref=db.backref('staff_members', lazy=True))
    user = db.relationship('User', backref=db.backref('staff_profile', uselist=False))

# 8. Students Model
class Student(db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.String(50), db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Active')
    photo_url = db.Column(db.Text)
    
    # Emergency contact details
    contact_name = db.Column(db.String(100))
    contact_relation = db.Column(db.String(50))
    contact_phone = db.Column(db.String(20))

    class_ = db.relationship('Class', backref=db.backref('students', lazy=True))
    department = db.relationship('Department', backref=db.backref('students', lazy=True))
    user = db.relationship('User', backref=db.backref('student_profile', uselist=False))

# 9. Staff Subject Assignment Model
class StaffSubjectAssignment(db.Model):
    __tablename__ = 'staff_subject_assignments'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(50), db.ForeignKey('staff.staff_id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('class_id', 'subject_id', name='_class_subject_assignment_uc'),)

    staff = db.relationship('Staff', backref=db.backref('assignments', lazy=True))
    class_ = db.relationship('Class', backref=db.backref('assignments', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('assignments', lazy=True))

# 10. Student Attendance Model
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    staff_id = db.Column(db.String(50), db.ForeignKey('staff.staff_id'), nullable=False)
    status = db.Column(db.String(20), nullable=False) # 'Present', 'Absent', 'Late'

    __table_args__ = (db.UniqueConstraint('student_id', 'date', 'subject_id', name='_student_attendance_uc'),)

    student = db.relationship('Student', backref=db.backref('attendance_records', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('attendance_records', lazy=True))
    staff = db.relationship('Staff', backref=db.backref('attendance_marked', lazy=True))

# 11. Staff Attendance Model
class StaffAttendance(db.Model):
    __tablename__ = 'staff_attendance'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(50), db.ForeignKey('staff.staff_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), nullable=False) # 'Present', 'Absent'
    working_hours = db.Column(db.Numeric(4, 2), default=0.0)

    staff = db.relationship('Staff', backref=db.backref('attendance_records', lazy=True))

# 12. Class Representatives Model
class ClassRepresentative(db.Model):
    __tablename__ = 'class_representatives'
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.student_id'), nullable=False)

    class_ = db.relationship('Class', backref=db.backref('representative', uselist=False))
    student = db.relationship('Student', backref=db.backref('represented_class', uselist=False))

# 13. System Announcements Model
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    author_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True) # nullable implies global notice

    author = db.relationship('User', backref=db.backref('announcements', lazy=True))
    department = db.relationship('Department', backref=db.backref('announcements', lazy=True))

# 14. Leave Applications Model
class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending') # 'Pending', 'Approved', 'Rejected'

    user = db.relationship('User', backref=db.backref('leave_applications', lazy=True))

# 15. Class Timetable Model
class Timetable(db.Model):
    __tablename__ = 'timetables'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    day_of_week = db.Column(db.String(15), nullable=False) # e.g. "Monday"
    
    # Periods mapped to Subject IDs
    period_1_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    period_2_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    period_3_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    period_4_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)

    class_ = db.relationship('Class', backref=db.backref('timetables', lazy=True))
    p1 = db.relationship('Subject', foreign_keys=[period_1_id])
    p2 = db.relationship('Subject', foreign_keys=[period_2_id])
    p3 = db.relationship('Subject', foreign_keys=[period_3_id])
    p4 = db.relationship('Subject', foreign_keys=[period_4_id])

# 16. System Settings Model
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(100), nullable=False)
