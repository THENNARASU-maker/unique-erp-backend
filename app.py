import os
import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
import bcrypt

load_dotenv()

from models import (
    db, Role, User, Department, Course, Class, Subject,
    Staff, Student, StaffSubjectAssignment, Attendance,
    StaffAttendance, ClassRepresentative, Announcement, LeaveApplication,
    Timetable, SystemSetting
)

app = Flask(__name__)
CORS(app)

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'unilog-default-secret-key-999')
PORT = int(os.getenv('PORT', 5000))

# Configure database
db_url = os.getenv('DATABASE_URL', 'sqlite:///unilog.db')
if 'postgresql' in db_url or 'postgres' in db_url:
    # URL-encode spaces in password/username if present
    if ' ' in db_url:
        parts = db_url.split('@', 1)
        if len(parts) == 2:
            creds, host = parts
            proto_parts = creds.split('://', 1)
            if len(proto_parts) == 2:
                proto, user_pass = proto_parts
                user_pass_parts = user_pass.split(':', 1)
                if len(user_pass_parts) == 2:
                    username, password = user_pass_parts
                    import urllib.parse
                    encoded_pass = urllib.parse.quote(password)
                    db_url = f"{proto}://{username}:{encoded_pass}@{host}"

    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    if 'postgresql+pg8000://' in db_url:
        db_url = db_url.replace('postgresql+pg8000://', 'postgresql://', 1)
    elif 'postgresql+psycopg2://' in db_url:
        db_url = db_url.replace('postgresql+psycopg2://', 'postgresql://', 1)
    try:
        import psycopg2
    except ImportError:
        db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- Authentication Helpers & Decorators ---

def generate_token(user):
    payload = {
        'id': user.id,
        'name': user.name,
        'role': user.role.name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = db.session.get(User, data['id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
            req_role = current_user.role.name
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, req_role, *args, **kwargs)
    return decorated

# --- Seeding Logic ---

def seed_database():
    db.create_all()

    # 1. Seed Roles
    roles = ['Admin', 'HOD', 'AHOD', 'Staff', 'Student', 'CR']
    for role_name in roles:
        if not Role.query.filter_by(name=role_name).first():
            db.session.add(Role(name=role_name))
    db.session.commit()

    # 2. Seed Default Admin
    admin_role = Role.query.filter_by(name='Admin').first()
    if not db.session.get(User, 'ADMIN01'):
        admin_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8')
        admin_user = User(id='ADMIN01', name='System Administrator', password_hash=admin_hash, role_id=admin_role.id)
        db.session.add(admin_user)
    db.session.commit()

    # 3. Seed Settings
    default_settings = {
        'academic_year': '2025-2026',
        'semester': 'Odd Semester (Semester I/III/V)'
    }
    for k, v in default_settings.items():
        if not db.session.get(SystemSetting, k):
            db.session.add(SystemSetting(key=k, value=v))
    db.session.commit()

    # 4. Seed UG Departments
    depts = [
        'B.Sc. Computer Science',
        'B.Sc. Information Technology',
        'Bachelor of Computer Applications',
        'B.Sc. Mathematics',
        'Bachelor of Business Administration'
    ]
    for d_name in depts:
        if not Department.query.filter_by(name=d_name).first():
            db.session.add(Department(name=d_name))
    db.session.commit()

    # 5. Seed Courses inside Departments
    cs_dept = Department.query.filter_by(name='B.Sc. Computer Science').first()
    bca_dept = Department.query.filter_by(name='Bachelor of Computer Applications').first()
    it_dept = Department.query.filter_by(name='B.Sc. Information Technology').first()
    math_dept = Department.query.filter_by(name='B.Sc. Mathematics').first()
    bba_dept = Department.query.filter_by(name='Bachelor of Business Administration').first()

    courses_list = [
        {'name': 'B.Sc. Computer Science (Regular)', 'dept_id': cs_dept.id},
        {'name': 'Bachelor of Computer Applications (Regular)', 'dept_id': bca_dept.id},
        {'name': 'B.Sc. Information Technology (Regular)', 'dept_id': it_dept.id},
        {'name': 'B.Sc. Mathematics (Regular)', 'dept_id': math_dept.id},
        {'name': 'Bachelor of Business Administration (Regular)', 'dept_id': bba_dept.id}
    ]
    for c_data in courses_list:
        if not Course.query.filter_by(name=c_data['name']).first():
            db.session.add(Course(name=c_data['name'], department_id=c_data['dept_id']))
    db.session.commit()

    # 6. Seed HOD
    cs_course = Course.query.filter_by(name='B.Sc. Computer Science (Regular)').first()
    bca_course = Course.query.filter_by(name='Bachelor of Computer Applications (Regular)').first()
    it_course = Course.query.filter_by(name='B.Sc. Information Technology (Regular)').first()
    math_course = Course.query.filter_by(name='B.Sc. Mathematics (Regular)').first()
    bba_course = Course.query.filter_by(name='Bachelor of Business Administration (Regular)').first()

    hod_role = Role.query.filter_by(name='HOD').first()
    hod_id = 'HODCS01'
    if not db.session.get(User, hod_id):
        hod_hash = bcrypt.hashpw(b'cs123', bcrypt.gensalt()).decode('utf-8')
        hod_user = User(id=hod_id, name='Dr. Alan Turing', password_hash=hod_hash, role_id=hod_role.id)
        db.session.add(hod_user)
        db.session.commit()

        cs_dept.hod_id = hod_id
        
        hod_staff = Staff(
            staff_id=hod_id, name='Dr. Alan Turing', department_id=cs_dept.id,
            email='turing.hod@unilog.edu', phone='555-0301', status='Active', photo_url=''
        )
        db.session.add(hod_staff)
        db.session.commit()

    # 7. Seed AHOD
    ahod_role = Role.query.filter_by(name='AHOD').first()
    ahod_id = 'AHODCS01'
    if not db.session.get(User, ahod_id):
        ahod_hash = bcrypt.hashpw(b'cs123', bcrypt.gensalt()).decode('utf-8')
        ahod_user = User(id=ahod_id, name='Dr. Ada Lovelace', password_hash=ahod_hash, role_id=ahod_role.id)
        db.session.add(ahod_user)
        db.session.commit()

        cs_dept.ahod_id = ahod_id
        
        ahod_staff = Staff(
            staff_id=ahod_id, name='Dr. Ada Lovelace', department_id=cs_dept.id,
            email='lovelace.ahod@unilog.edu', phone='555-0302', status='Active', photo_url=''
        )
        db.session.add(ahod_staff)
        db.session.commit()

    # 8. Seed Staff
    staff_role = Role.query.filter_by(name='Staff').first()
    staff_id = 'STAFFCS01'
    if not db.session.get(User, staff_id):
        staff_hash = bcrypt.hashpw(b'staff123', bcrypt.gensalt()).decode('utf-8')
        staff_user = User(id=staff_id, name='Grace Hopper', password_hash=staff_hash, role_id=staff_role.id)
        db.session.add(staff_user)
        db.session.commit()

        staff = Staff(
            staff_id=staff_id, name='Grace Hopper', department_id=cs_dept.id,
            email='hopper@unilog.edu', phone='555-0303', status='Active', photo_url=''
        )
        db.session.add(staff)
        db.session.commit()

    # 9. Seed 3 classes for each Course
    all_classes_configs = [
        {'name': 'B.Sc. CS - I Year', 'course_id': cs_course.id, 'dept_id': cs_dept.id},
        {'name': 'B.Sc. CS - II Year', 'course_id': cs_course.id, 'dept_id': cs_dept.id},
        {'name': 'B.Sc. CS - III Year', 'course_id': cs_course.id, 'dept_id': cs_dept.id},
        
        {'name': 'BCA - I Year', 'course_id': bca_course.id, 'dept_id': bca_dept.id},
        {'name': 'BCA - II Year', 'course_id': bca_course.id, 'dept_id': bca_dept.id},
        {'name': 'BCA - III Year', 'course_id': bca_course.id, 'dept_id': bca_dept.id},

        {'name': 'B.Sc. IT - I Year', 'course_id': it_course.id, 'dept_id': it_dept.id},
        {'name': 'B.Sc. IT - II Year', 'course_id': it_course.id, 'dept_id': it_dept.id},
        {'name': 'B.Sc. IT - III Year', 'course_id': it_course.id, 'dept_id': it_dept.id},

        {'name': 'B.Sc. Math - I Year', 'course_id': math_course.id, 'dept_id': math_dept.id},
        {'name': 'B.Sc. Math - II Year', 'course_id': math_course.id, 'dept_id': math_dept.id},
        {'name': 'B.Sc. Math - III Year', 'course_id': math_course.id, 'dept_id': math_dept.id},

        {'name': 'BBA - I Year', 'course_id': bba_course.id, 'dept_id': bba_dept.id},
        {'name': 'BBA - II Year', 'course_id': bba_course.id, 'dept_id': bba_dept.id},
        {'name': 'BBA - III Year', 'course_id': bba_course.id, 'dept_id': bba_dept.id}
    ]
    for c_conf in all_classes_configs:
        if not Class.query.filter_by(name=c_conf['name']).first():
            db.session.add(Class(name=c_conf['name'], course_id=c_conf['course_id'], department_id=c_conf['dept_id']))
    db.session.commit()

    class_obj = Class.query.filter_by(name='B.Sc. CS - I Year').first()

    # 10. Seed Student
    student_role = Role.query.filter_by(name='Student').first()
    student_id = 'STUCS01'
    if not db.session.get(User, student_id):
        student_hash = bcrypt.hashpw(b'student123', bcrypt.gensalt()).decode('utf-8')
        student_user = User(id=student_id, name='Dennis Ritchie', password_hash=student_hash, role_id=student_role.id)
        db.session.add(student_user)
        db.session.commit()

        student = Student(
            student_id=student_id, name='Dennis Ritchie', class_id=class_obj.id, department_id=cs_dept.id,
            email='ritchie@unilog.edu', phone='555-0101', status='Active', photo_url='',
            contact_name='Ritchie Sr.', contact_relation='Father', contact_phone='555-0102'
        )
        db.session.add(student)
        db.session.commit()

    # 11. Seed CR
    cr_id = 'CRCS01'
    if not db.session.get(User, cr_id):
        cr_hash = bcrypt.hashpw(b'cr123', bcrypt.gensalt()).decode('utf-8')
        cr_user = User(id=cr_id, name='Ken Thompson', password_hash=cr_hash, role_id=Role.query.filter_by(name='CR').first().id)
        db.session.add(cr_user)
        db.session.commit()

        student = Student(
            student_id=cr_id, name='Ken Thompson', class_id=class_obj.id, department_id=cs_dept.id,
            email='thompson@unilog.edu', phone='555-0105', status='Active', photo_url='',
            contact_name='Thompson Sr.', contact_relation='Father', contact_phone='555-0106'
        )
        db.session.add(student)
        db.session.commit()

        cr_record = ClassRepresentative(class_id=class_obj.id, student_id=cr_id)
        db.session.add(cr_record)
        db.session.commit()

    # 12. Seed Subjects and Assignments
    subjects = ['Python Programming', 'Database Systems', 'Discrete Mathematics']
    for sub_name in subjects:
        if not Subject.query.filter_by(name=sub_name, class_id=class_obj.id).first():
            subject = Subject(name=sub_name, class_id=class_obj.id, department_id=cs_dept.id)
            db.session.add(subject)
    db.session.commit()

    python_sub = Subject.query.filter_by(name='Python Programming', class_id=class_obj.id).first()
    db_sub = Subject.query.filter_by(name='Database Systems', class_id=class_obj.id).first()
    discrete_sub = Subject.query.filter_by(name='Discrete Mathematics', class_id=class_obj.id).first()

    if python_sub and not StaffSubjectAssignment.query.filter_by(subject_id=python_sub.id).first():
        db.session.add(StaffSubjectAssignment(staff_id=staff_id, class_id=class_obj.id, subject_id=python_sub.id))
    if db_sub and not StaffSubjectAssignment.query.filter_by(subject_id=db_sub.id).first():
        db.session.add(StaffSubjectAssignment(staff_id=hod_id, class_id=class_obj.id, subject_id=db_sub.id))
    if discrete_sub and not StaffSubjectAssignment.query.filter_by(subject_id=discrete_sub.id).first():
        db.session.add(StaffSubjectAssignment(staff_id=ahod_id, class_id=class_obj.id, subject_id=discrete_sub.id))
    db.session.commit()

    # 13. Seed Timetable
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in days:
        if not Timetable.query.filter_by(class_id=class_obj.id, day_of_week=day).first():
            tt = Timetable(
                class_id=class_obj.id,
                day_of_week=day,
                period_1_id=python_sub.id if python_sub else None,
                period_2_id=db_sub.id if db_sub else None,
                period_3_id=discrete_sub.id if discrete_sub else None,
                period_4_id=python_sub.id if python_sub else None
            )
            db.session.add(tt)
    db.session.commit()

    # 14. Seed Announcement
    if not Announcement.query.filter_by(title='College Reopening & Induction Details').first():
        db.session.add(Announcement(
            title='College Reopening & Induction Details',
            content='Dear students, academic terms for Odd Semester begins from July 10th. Attendance is mandatory.',
            date=datetime.date.today(),
            author_id='ADMIN01'
        ))
    db.session.commit()

# Ensure database tables exist and are seeded on startup (runs under Gunicorn/Render too)
with app.app_context():
    db.create_all()
    seed_database()

# --- Authentication APIs ---

# User Login
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'id' not in data or 'password' not in data:
        return jsonify({'error': 'Missing credentials'}), 400

    user_id = data['id'].upper().strip()
    password = data['password']

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Invalid ID or password'}), 401

    # Check portal boundary if present
    portal = data.get('portal')
    role_name = data.get('role')

    if portal:
        if portal == 'Student' and user.role.name not in ['Student', 'CR']:
             return jsonify({'error': 'Invalid Student or CR credentials'}), 401
        elif portal == 'Staff' and user.role.name not in ['Admin', 'Staff', 'HOD', 'AHOD']:
             return jsonify({'error': 'Invalid Administrator or Staff credentials'}), 401
    elif role_name:
        if user.role.name != role_name:
             return jsonify({'error': f'Invalid ID or user role is not {role_name}'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Incorrect password'}), 401

    token = generate_token(user)
    
    dept_id = None
    if user.role.name in ['HOD', 'AHOD', 'Staff']:
        staff = db.session.get(Staff, user_id)
        if staff: dept_id = staff.department_id
    elif user.role.name in ['Student', 'CR']:
        stud = db.session.get(Student, user_id)
        if stud: dept_id = stud.department_id

    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'name': user.name,
            'role': user.role.name,
            'department_id': dept_id
        }
    })

# Online Registration Endpoint
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'id' not in data or 'name' not in data or 'email' not in data or 'password' not in data or 'role' not in data:
        return jsonify({'error': 'Missing registration parameters'}), 400

    u_id = data['id'].strip().upper()
    name = data['name'].strip()
    email = data['email'].strip()
    password = data['password']
    role_name = data['role'] # 'Student' or 'Staff'

    if role_name not in ['Student', 'Staff']:
        return jsonify({'error': 'Public signup restricts to Student or Staff roles'}), 400

    if db.session.get(User, u_id):
        return jsonify({'error': 'User ID / ID already exists'}), 400

    # Retrieve associated department/class
    target_role = Role.query.filter_by(name=role_name).first()
    pass_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create Core User
    new_user = User(id=u_id, name=name, password_hash=pass_hash, role_id=target_role.id)
    db.session.add(new_user)
    db.session.commit()

    if role_name == 'Student':
        class_id = int(data.get('class_id', 0))
        class_obj = db.session.get(Class, class_id)
        if not class_obj:
            return jsonify({'error': 'Class ID not found'}), 400

        student = Student(
            student_id=u_id, name=name, class_id=class_id, department_id=class_obj.department_id,
            email=email, phone=data.get('phone', ''), status='Active', photo_url='',
            contact_name=data.get('contact_name', ''), contact_relation=data.get('contact_relation', ''),
            contact_phone=data.get('contact_phone', '')
        )
        db.session.add(student)
    else:
        dept_id = int(data.get('department_id', 0))
        dept = db.session.get(Department, dept_id)
        if not dept:
            return jsonify({'error': 'Department not found'}), 400

        staff = Staff(
            staff_id=u_id, name=name, department_id=dept_id,
            email=email, phone=data.get('phone', ''), status='Active', photo_url=''
        )
        db.session.add(staff)

    db.session.commit()
    return jsonify({'message': 'Registration completed successfully! Login now.'}), 201

# Change Password API
@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password(current_user, role):
    data = request.get_json()
    if not data or 'old_password' not in data or 'new_password' not in data:
        return jsonify({'error': 'Missing password fields'}), 400

    old = data['old_password']
    new = data['new_password']

    if not bcrypt.checkpw(old.encode('utf-8'), current_user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Incorrect old password'}), 400

    new_hash = bcrypt.hashpw(new.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    current_user.password_hash = new_hash
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})

# --- Dashboard API ---
@app.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_user, role):
    today = datetime.date.today()

    if role == 'Admin':
        total_depts = Department.query.count()
        total_staff = Staff.query.count()
        total_students = Student.query.count()
        
        present_count = Attendance.query.filter_by(date=today, status='Present').count()
        absent_count = Attendance.query.filter_by(date=today, status='Absent').count()
        late_count = Attendance.query.filter_by(date=today, status='Late').count()
        
        return jsonify({
            'totalDepartments': total_depts,
            'totalStaff': total_staff,
            'totalStudents': total_students,
            'todayAttendance': {
                'present': present_count,
                'absent': absent_count,
                'late': late_count
            }
        })

    elif role in ['HOD', 'AHOD']:
        staff_profile = db.session.get(Staff, current_user.id)
        if not staff_profile:
            return jsonify({'error': 'Staff profile not found'}), 404
        
        dept_id = staff_profile.department_id
        staff_count = Staff.query.filter_by(department_id=dept_id).count()
        student_count = Student.query.filter_by(department_id=dept_id).count()
        
        stud_att_present = Attendance.query.join(Student).filter(
            Student.department_id == dept_id, Attendance.date == today, Attendance.status == 'Present'
        ).count()
        stud_att_absent = Attendance.query.join(Student).filter(
            Student.department_id == dept_id, Attendance.date == today, Attendance.status == 'Absent'
        ).count()
        
        staff_present = StaffAttendance.query.join(Staff).filter(
            Staff.department_id == dept_id, StaffAttendance.date == today, StaffAttendance.status == 'Present'
        ).count()
        staff_absent = StaffAttendance.query.join(Staff).filter(
            Staff.department_id == dept_id, StaffAttendance.date == today, StaffAttendance.status == 'Absent'
        ).count()

        return jsonify({
            'departmentStaffCount': staff_count,
            'departmentStudentCount': student_count,
            'studentAttendance': { 'present': stud_att_present, 'absent': stud_att_absent, 'late': 0 },
            'staffAttendance': { 'present': staff_present, 'absent': staff_absent }
        })

    elif role == 'Staff':
        staff_profile = db.session.get(Staff, current_user.id)
        if not staff_profile:
            return jsonify({'error': 'Staff profile not found'}), 404

        assignments = StaffSubjectAssignment.query.filter_by(staff_id=current_user.id).all()
        assigned_classes_list = []
        class_ids = set()
        
        for a in assignments:
            if a.class_id not in class_ids:
                class_ids.add(a.class_id)
                assigned_classes_list.append({ 'id': a.class_.id, 'name': a.class_.name })

        today_att_count = Attendance.query.filter_by(date=today, staff_id=current_user.id).count()

        return jsonify({
            'assignedClasses': assigned_classes_list,
            'todayAttendanceCount': today_att_count
        })

    elif role in ['Student', 'CR']:
        student_profile = db.session.get(Student, current_user.id)
        if not student_profile:
            return jsonify({'error': 'Student profile not found'}), 404

        total_sessions = Attendance.query.filter_by(student_id=current_user.id).count()
        present_sessions = Attendance.query.filter(
            Attendance.student_id == current_user.id, Attendance.status.in_(['Present', 'Late'])
        ).count()
        
        attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 100.0

        assignments = StaffSubjectAssignment.query.filter_by(class_id=student_profile.class_id).all()
        subjects_list = []
        for a in assignments:
            subjects_list.append({
                'subject': a.subject.name,
                'faculty': a.staff.name,
                'email': a.staff.email
            })

        return jsonify({
            'profile': {
                'student_id': student_profile.student_id,
                'name': student_profile.name,
                'email': student_profile.email,
                'phone': student_profile.phone,
                'class': student_profile.class_.name,
                'department': student_profile.department.name,
                'photo_url': student_profile.photo_url or ''
            },
            'attendancePercentage': round(attendance_percentage, 1),
            'subjects': subjects_list
        })

    return jsonify({'error': 'Unknown dashboard role'}), 400

# --- Course CRUD Management ---

@app.route('/api/courses', methods=['GET'])
@token_required
def get_courses(current_user, role):
    dept_id = request.args.get('department_id')
    query = Course.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)

    # Filter boundaries
    if role in ['HOD', 'AHOD', 'Staff']:
        mgr = db.session.get(Staff, current_user.id)
        query = query.filter_by(department_id=mgr.department_id)

    courses = query.all()
    output = []
    for c in courses:
        output.append({
            'id': c.id,
            'name': c.name,
            'department_id': c.department_id,
            'department_name': c.department.name
        })
    return jsonify(output)

@app.route('/api/courses', methods=['POST'])
@token_required
def create_course(current_user, role):
    if role != 'Admin':
        return jsonify({'error': 'Admin permissions required'}), 403

    data = request.get_json()
    if not data or 'name' not in data or 'department_id' not in data:
        return jsonify({'error': 'Missing fields'}), 400

    name = data['name'].strip()
    dept_id = int(data['department_id'])

    if Course.query.filter_by(name=name).first():
        return jsonify({'error': 'Course name already exists'}), 400

    new_course = Course(name=name, department_id=dept_id)
    db.session.add(new_course)
    db.session.commit()
    return jsonify({'message': 'Course created successfully'}), 201

@app.route('/api/courses/<int:id>', methods=['PUT'])
@token_required
def update_course(current_user, role, id):
    if role != 'Admin':
        return jsonify({'error': 'Admin permissions required'}), 403

    course = db.session.get(Course, id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    data = request.get_json()
    if 'name' in data:
        course.name = data['name'].strip()
    if 'department_id' in data:
        course.department_id = int(data['department_id'])

    db.session.commit()
    return jsonify({'message': 'Course details updated successfully'})

@app.route('/api/courses/<int:id>', methods=['DELETE'])
@token_required
def delete_course(current_user, role, id):
    if role != 'Admin':
        return jsonify({'error': 'Admin permissions required'}), 403

    course = db.session.get(Course, id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    db.session.delete(course)
    db.session.commit()
    return jsonify({'message': 'Course deleted successfully'})

# --- Leave Applications Management ---

@app.route('/api/leaves', methods=['GET'])
@token_required
def get_leaves(current_user, role):
    query = LeaveApplication.query

    if role in ['Student', 'Staff']:
        query = query.filter_by(user_id=current_user.id)
    elif role in ['HOD', 'AHOD']:
        mgr = db.session.get(Staff, current_user.id)
        # join query on users and staff to filter matching department
        query = query.join(User).join(Staff, Staff.staff_id == User.id, isouter=True).join(Student, Student.student_id == User.id, isouter=True).filter(
            (Staff.department_id == mgr.department_id) | (Student.department_id == mgr.department_id)
        )

    leaves = query.all()
    output = []
    for l in leaves:
        output.append({
            'id': l.id,
            'user_id': l.user_id,
            'user_name': l.user.name,
            'role': l.user.role.name,
            'start_date': l.start_date.isoformat(),
            'end_date': l.end_date.isoformat(),
            'reason': l.reason,
            'status': l.status
        })
    return jsonify(output)

@app.route('/api/leaves', methods=['POST'])
@token_required
def apply_leave(current_user, role):
    data = request.get_json()
    if not data or 'start_date' not in data or 'end_date' not in data or 'reason' not in data:
        return jsonify({'error': 'Missing leave fields'}), 400

    start = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    reason = data['reason'].strip()

    new_app = LeaveApplication(user_id=current_user.id, start_date=start, end_date=end, reason=reason)
    db.session.add(new_app)
    db.session.commit()
    return jsonify({'message': 'Leave application submitted successfully'}), 201

@app.route('/api/leaves/<int:id>', methods=['PUT'])
@token_required
def process_leave(current_user, role, id):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Unauthorized to process leave requests'}), 403

    leave = db.session.get(LeaveApplication, id)
    if not leave:
        return jsonify({'error': 'Leave request not found'}), 404

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status'}), 400

    status = data['status'] # Approved, Rejected
    if status not in ['Approved', 'Rejected']:
         return jsonify({'error': 'Invalid status'}), 400

    leave.status = status
    db.session.commit()
    return jsonify({'message': f'Leave application status updated to {status}'})

# --- Timetables APIs ---

@app.route('/api/timetable', methods=['GET'])
@token_required
def get_timetable(current_user, role):
    class_id = request.args.get('class_id')
    if not class_id:
        if role in ['Student', 'CR']:
            stud = db.session.get(Student, current_user.id)
            class_id = stud.class_id
        else:
             return jsonify({'error': 'class_id parameter is required'}), 400

    tts = Timetable.query.filter_by(class_id=class_id).all()
    output = []
    for t in tts:
        output.append({
            'day': t.day_of_week,
            'period_1': t.p1.name if t.p1 else 'Free Period',
            'period_2': t.p2.name if t.p2 else 'Free Period',
            'period_3': t.p3.name if t.p3 else 'Free Period',
            'period_4': t.p4.name if t.p4 else 'Free Period'
        })
    return jsonify(output)

@app.route('/api/timetable', methods=['POST'])
@token_required
def configure_timetable(current_user, role):
    # Managed by HODs, AHODs or Admins
    if role not in ['Admin', 'HOD', 'AHOD']:
         return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data or 'class_id' not in data or 'day_of_week' not in data:
         return jsonify({'error': 'Missing fields'}), 400

    class_id = int(data['class_id'])
    day = data['day_of_week'].strip()
    p1 = data.get('period_1_id')
    p2 = data.get('period_2_id')
    p3 = data.get('period_3_id')
    p4 = data.get('period_4_id')

    # check if day schedule exists
    tt = Timetable.query.filter_by(class_id=class_id, day_of_week=day).first()
    if tt:
        tt.period_1_id = p1 if p1 else None
        tt.period_2_id = p2 if p2 else None
        tt.period_3_id = p3 if p3 else None
        tt.period_4_id = p4 if p4 else None
    else:
        tt = Timetable(class_id=class_id, day_of_week=day, period_1_id=p1, period_2_id=p2, period_3_id=p3, period_4_id=p4)
        db.session.add(tt)

    db.session.commit()
    return jsonify({'message': 'Timetable day config saved successfully'})

# --- Announcements APIs ---

@app.route('/api/announcements', methods=['GET'])
@token_required
def get_announcements(current_user, role):
    query = Announcement.query
    
    # Filter global or own department announcements
    if role in ['HOD', 'AHOD', 'Staff']:
        mgr = db.session.get(Staff, current_user.id)
        query = query.filter((Announcement.department_id == None) | (Announcement.department_id == mgr.department_id))
    elif role in ['Student', 'CR']:
        stud = db.session.get(Student, current_user.id)
        query = query.filter((Announcement.department_id == None) | (Announcement.department_id == stud.department_id))

    notices = query.order_by(Announcement.id.desc()).all()
    output = []
    for n in notices:
        output.append({
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'date': n.date.isoformat(),
            'author': n.author.name,
            'department_name': n.department.name if n.department else 'Global'
        })
    return jsonify(output)

@app.route('/api/announcements', methods=['POST'])
@token_required
def create_announcement(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Unauthorized to publish announcements'}), 403

    data = request.get_json()
    if not data or 'title' not in data or 'content' not in data:
         return jsonify({'error': 'Missing title or content'}), 400

    title = data['title'].strip()
    content = data['content'].strip()
    
    dept_id = None
    if role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         dept_id = mgr.department_id
    else:
         d_val = data.get('department_id')
         dept_id = int(d_val) if d_val else None

    new_notice = Announcement(
        title=title, content=content, date=datetime.date.today(),
        author_id=current_user.id, department_id=dept_id
    )
    db.session.add(new_notice)
    db.session.commit()
    return jsonify({'message': 'Notice board announcement posted successfully'})

# --- System Settings APIs ---

@app.route('/api/settings', methods=['GET'])
@token_required
def get_settings(current_user, role):
    settings = SystemSetting.query.all()
    output = {}
    for s in settings:
         output[s.key] = s.value
    return jsonify(output)

@app.route('/api/settings', methods=['POST'])
@token_required
def update_settings(current_user, role):
    if role != 'Admin':
        return jsonify({'error': 'Admin permissions required'}), 403

    data = request.get_json()
    if not data:
         return jsonify({'error': 'No fields provided'}), 400

    for k, v in data.items():
         s = db.session.get(SystemSetting, k)
         if s:
              s.value = str(v)
         else:
              db.session.add(SystemSetting(key=k, value=str(v)))

    db.session.commit()
    return jsonify({'message': 'System settings updated successfully'})

# --- Database Backup & Restore ---

@app.route('/api/admin/backup', methods=['GET'])
@token_required
def get_backup_log(current_user, role):
    if role != 'Admin':
         return jsonify({'error': 'Admin permissions required'}), 403

    backup = {
        'departments': [{'id': d.id, 'name': d.name, 'hod_id': d.hod_id, 'ahod_id': d.ahod_id} for d in Department.query.all()],
        'courses': [{'id': c.id, 'name': c.name, 'department_id': c.department_id} for c in Course.query.all()],
        'classes': [{'id': c.id, 'name': c.name, 'course_id': c.course_id, 'department_id': c.department_id} for c in Class.query.all()],
        'subjects': [{'id': s.id, 'name': s.name, 'class_id': s.class_id, 'department_id': s.department_id} for s in Subject.query.all()],
        'users': [{'id': u.id, 'name': u.name, 'password_hash': u.password_hash, 'role_id': u.role_id} for u in User.query.all()],
        'students': [{
            'student_id': s.student_id, 'name': s.name, 'class_id': s.class_id, 'department_id': s.department_id,
            'email': s.email, 'phone': s.phone, 'status': s.status, 'photo_url': s.photo_url,
            'contact_name': s.contact_name, 'contact_relation': s.contact_relation, 'contact_phone': s.contact_phone
        } for s in Student.query.all()],
        'staff': [{
            'staff_id': s.staff_id, 'name': s.name, 'department_id': s.department_id,
            'email': s.email, 'phone': s.phone, 'status': s.status, 'photo_url': s.photo_url
        } for s in Staff.query.all()],
        'assignments': [{'staff_id': a.staff_id, 'class_id': a.class_id, 'subject_id': a.subject_id} for a in StaffSubjectAssignment.query.all()]
    }
    return jsonify(backup)

@app.route('/api/admin/restore', methods=['POST'])
@token_required
def restore_backup(current_user, role):
    if role != 'Admin':
         return jsonify({'error': 'Admin permissions required'}), 403

    data = request.get_json()
    if not data:
         return jsonify({'error': 'No backup data payload supplied'}), 400

    try:
        # Wipe existing tables except system configurations
        ClassRepresentative.query.delete()
        StaffSubjectAssignment.query.delete()
        Attendance.query.delete()
        StaffAttendance.query.delete()
        LeaveApplication.query.delete()
        Announcement.query.delete()
        Timetable.query.delete()
        Student.query.delete()
        Staff.query.delete()
        Subject.query.delete()
        Class.query.delete()
        Course.query.delete()
        Department.query.delete()
        User.query.delete()
        db.session.commit()

        # Restore in order
        for u in data['users']:
             db.session.add(User(id=u['id'], name=u['name'], password_hash=u['password_hash'], role_id=u['role_id']))
        db.session.commit()

        for d in data['departments']:
             db.session.add(Department(id=d['id'], name=d['name'], hod_id=d['hod_id'], ahod_id=d['ahod_id']))
        db.session.commit()

        for c in data['courses']:
             db.session.add(Course(id=c['id'], name=c['name'], department_id=c['department_id']))
        db.session.commit()

        for c in data['classes']:
             db.session.add(Class(id=c['id'], name=c['name'], course_id=c['course_id'], department_id=c['department_id']))
        db.session.commit()

        for s in data['subjects']:
             db.session.add(Subject(id=s['id'], name=s['name'], class_id=s['class_id'], department_id=s['department_id']))
        db.session.commit()

        for s in data['students']:
             db.session.add(Student(
                  student_id=s['student_id'], name=s['name'], class_id=s['class_id'], department_id=s['department_id'],
                  email=s['email'], phone=s['phone'], status=s['status'], photo_url=s['photo_url'],
                  contact_name=s['contact_name'], contact_relation=s['contact_relation'], contact_phone=s['contact_phone']
             ))

        for s in data['staff']:
             db.session.add(Staff(
                  staff_id=s['staff_id'], name=s['name'], department_id=s['department_id'],
                  email=s['email'], phone=s['phone'], status=s['status'], photo_url=s['photo_url']
             ))
        db.session.commit()

        for a in data['assignments']:
             db.session.add(StaffSubjectAssignment(staff_id=a['staff_id'], class_id=a['class_id'], subject_id=a['subject_id']))
        db.session.commit()

        return jsonify({'message': 'ERP system data restored successfully'})
    except Exception as e:
         db.session.rollback()
         return jsonify({'error': f'Failed to restore backup log: {str(e)}'}), 500

# --- Standard CRUD Endpoints overrides ---

# Departments
@app.route('/api/departments', methods=['GET'])
@token_required
def get_departments(current_user, role):
    if role in ['Student', 'CR']:
        return jsonify({'error': 'Access denied'}), 403
    depts = Department.query.all()
    output = []
    for d in depts:
        output.append({
            'id': d.id,
            'name': d.name,
            'hod': d.hod.name if d.hod else 'None',
            'hod_id': d.hod_id or '',
            'ahod': d.ahod.name if d.ahod else 'None',
            'ahod_id': d.ahod_id or ''
        })
    return jsonify(output)

@app.route('/api/departments', methods=['POST'])
@token_required
def create_department(current_user, role):
    if role != 'Admin':
        return jsonify({'error': 'Admin permission required'}), 403
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing department name'}), 400
    name = data['name'].strip()
    if Department.query.filter_by(name=name).first():
        return jsonify({'error': 'Department already exists'}), 400
    dept = Department(name=name)
    db.session.add(dept)
    db.session.commit()
    return jsonify({'message': 'Department created successfully'}), 201

@app.route('/api/departments/<int:id>', methods=['PUT'])
@token_required
def update_department(current_user, role, id):
    if role != 'Admin':
        return jsonify({'error': 'Admin permission required'}), 403
    dept = db.session.get(Department, id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    data = request.get_json()
    if 'name' in data:
         dept.name = data['name'].strip()

    hod_role = Role.query.filter_by(name='HOD').first()
    ahod_role = Role.query.filter_by(name='AHOD').first()
    staff_role = Role.query.filter_by(name='Staff').first()

    if 'hod_id' in data:
         new_hod_id = data['hod_id'] if data['hod_id'] != '' else None
         old_hod_id = dept.hod_id
         
         # Demote old HOD to Staff (if they are not HOD/AHOD of another department)
         if old_hod_id and old_hod_id != new_hod_id:
              other_hod = Department.query.filter(Department.id != id, Department.hod_id == old_hod_id).first()
              other_ahod = Department.query.filter(Department.ahod_id == old_hod_id).first()
              if not other_hod and not other_ahod:
                   u_old = db.session.get(User, old_hod_id)
                   if u_old:
                        u_old.role_id = staff_role.id
         
         # Promote new HOD to HOD role
         if new_hod_id:
              u_new = db.session.get(User, new_hod_id)
              if u_new:
                   u_new.role_id = hod_role.id
         
         dept.hod_id = new_hod_id

    if 'ahod_id' in data:
         new_ahod_id = data['ahod_id'] if data['ahod_id'] != '' else None
         old_ahod_id = dept.ahod_id
         
         # Demote old AHOD to Staff
         if old_ahod_id and old_ahod_id != new_ahod_id:
              other_hod = Department.query.filter(Department.hod_id == old_ahod_id).first()
              other_ahod = Department.query.filter(Department.id != id, Department.ahod_id == old_ahod_id).first()
              if not other_hod and not other_ahod:
                   u_old = db.session.get(User, old_ahod_id)
                   if u_old:
                        u_old.role_id = staff_role.id
         
         # Promote new AHOD to AHOD role
         if new_ahod_id:
              u_new = db.session.get(User, new_ahod_id)
              if u_new:
                   u_new.role_id = ahod_role.id
                   
         dept.ahod_id = new_ahod_id

    db.session.commit()
    return jsonify({'message': 'Department updated successfully'})

@app.route('/api/departments/<int:id>', methods=['DELETE'])
@token_required
def delete_department(current_user, role, id):
    if role != 'Admin':
        return jsonify({'error': 'Admin permission required'}), 403
    dept = db.session.get(Department, id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404
    db.session.delete(dept)
    db.session.commit()
    return jsonify({'message': 'Department deleted successfully'})

# Classes
@app.route('/api/classes', methods=['GET'])
@token_required
def get_classes(current_user, role):
    if role in ['Student', 'CR']:
        student = db.session.get(Student, current_user.id)
        classes = Class.query.filter_by(id=student.class_id).all() if student else []
    elif role in ['HOD', 'AHOD', 'Staff']:
        staff = db.session.get(Staff, current_user.id)
        classes = Class.query.filter_by(department_id=staff.department_id).all() if staff else []
    else:
        classes = Class.query.all()

    output = []
    for c in classes:
        rep = ClassRepresentative.query.get(c.id)
        rep_name = rep.student.name if rep else 'None'
        output.append({
            'id': c.id,
            'name': c.name,
            'course_id': c.course_id or '',
            'course_name': c.course.name if c.course else 'No Course',
            'department_id': c.department_id,
            'department': c.department.name,
            'representative': rep_name,
            'representative_id': rep.student_id if rep else ''
        })
    return jsonify(output)

@app.route('/api/classes', methods=['POST'])
@token_required
def create_class(current_user, role):
    if role != 'Admin':
        return jsonify({'error': 'Admin permission required'}), 403
    data = request.get_json()
    if not data or 'name' not in data or 'department_id' not in data:
        return jsonify({'error': 'Missing fields'}), 400
    name = data['name'].strip()
    dept_id = int(data['department_id'])
    course_id = int(data['course_id']) if data.get('course_id') else None

    if Class.query.filter_by(name=name).first():
        return jsonify({'error': 'Class name already exists'}), 400

    new_class = Class(name=name, course_id=course_id, department_id=dept_id)
    db.session.add(new_class)
    db.session.commit()
    return jsonify({'message': 'Class created successfully'}), 201

@app.route('/api/classes/<int:id>', methods=['PUT'])
@token_required
def update_class(current_user, role, id):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Unauthorized'}), 403
    class_obj = db.session.get(Class, id)
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    data = request.get_json()

    if role in ['HOD', 'AHOD']:
        staff = db.session.get(Staff, current_user.id)
        if class_obj.department_id != staff.department_id:
             return jsonify({'error': 'Cannot manage other department classes'}), 403

    if 'name' in data and role == 'Admin':
        class_obj.name = data['name'].strip()
    if 'course_id' in data and role == 'Admin':
        class_obj.course_id = int(data['course_id']) if data['course_id'] else None

    if 'representative_id' in data:
        rep_id = data['representative_id']
        cr_role = Role.query.filter_by(name='CR').first()
        student_role = Role.query.filter_by(name='Student').first()
        
        cr_rec = ClassRepresentative.query.get(id)
        old_cr_id = cr_rec.student_id if cr_rec else None

        if rep_id == '':
             if old_cr_id:
                  u_old = db.session.get(User, old_cr_id)
                  if u_old:
                       u_old.role_id = student_role.id
             ClassRepresentative.query.filter_by(class_id=id).delete()
        else:
             student = db.session.get(Student, rep_id)
             if not student or student.class_id != id:
                  return jsonify({'error': 'Representative must be a student in this class'}), 400
             
             if old_cr_id and old_cr_id != rep_id:
                  u_old = db.session.get(User, old_cr_id)
                  if u_old:
                       u_old.role_id = student_role.id
                       
             if cr_rec:
                  cr_rec.student_id = rep_id
             else:
                  db.session.add(ClassRepresentative(class_id=id, student_id=rep_id))
             
             u = db.session.get(User, rep_id)
             if u:
                  u.role_id = cr_role.id

    db.session.commit()
    return jsonify({'message': 'Class updated successfully'})

@app.route('/api/classes/<int:id>', methods=['DELETE'])
@token_required
def delete_class(current_user, role, id):
    if role != 'Admin':
         return jsonify({'error': 'Admin permission required'}), 403
    class_obj = db.session.get(Class, id)
    if not class_obj:
         return jsonify({'error': 'Class not found'}), 404
    db.session.delete(class_obj)
    db.session.commit()
    return jsonify({'message': 'Class deleted successfully'})

# Subjects
@app.route('/api/subjects', methods=['GET'])
@token_required
def get_subjects(current_user, role):
    dept_id = request.args.get('department_id')
    class_id = request.args.get('class_id')
    query = Subject.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)
    if class_id:
        query = query.filter_by(class_id=class_id)
    if role in ['HOD', 'AHOD', 'Staff']:
        staff = db.session.get(Staff, current_user.id)
        query = query.filter_by(department_id=staff.department_id)
    elif role in ['Student', 'CR']:
        stud = db.session.get(Student, current_user.id)
        query = query.filter_by(class_id=stud.class_id)

    subjects = query.all()
    output = []
    for s in subjects:
        assign = StaffSubjectAssignment.query.filter_by(subject_id=s.id).first()
        output.append({
            'id': s.id,
            'name': s.name,
            'class_id': s.class_id,
            'class_name': s.class_.name,
            'department_id': s.department_id,
            'department_name': s.department.name,
            'assigned_staff': assign.staff.name if assign else 'Unassigned',
            'assigned_staff_id': assign.staff_id if assign else ''
        })
    return jsonify(output)

@app.route('/api/subjects', methods=['POST'])
@token_required
def create_subject(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json()
    if not data or 'name' not in data or 'class_id' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    name = data['name'].strip()
    class_id = int(data['class_id'])
    class_obj = db.session.get(Class, class_id)
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404

    dept_id = class_obj.department_id
    if role in ['HOD', 'AHOD']:
        staff = db.session.get(Staff, current_user.id)
        if dept_id != staff.department_id:
             return jsonify({'error': 'Cannot manage other departments'}), 403

    if Subject.query.filter_by(name=name, class_id=class_id).first():
        return jsonify({'error': 'Subject already exists in this class'}), 400

    subject = Subject(name=name, class_id=class_id, department_id=dept_id)
    db.session.add(subject)
    db.session.commit()
    return jsonify({'message': 'Subject created successfully'}), 201

# Subject assign faculty
@app.route('/api/subjects/assign', methods=['POST'])
@token_required
def assign_subject_staff(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json()
    if not data or 'subject_id' not in data or 'staff_id' not in data:
         return jsonify({'error': 'Missing parameters'}), 400

    sub_id = int(data['subject_id'])
    staff_id = data['staff_id'].strip().upper()

    subject = db.session.get(Subject, sub_id)
    staff = db.session.get(Staff, staff_id) if staff_id != '' else None

    if not subject:
         return jsonify({'error': 'Subject not found'}), 404

    if role in ['HOD', 'AHOD']:
        mgr = db.session.get(Staff, current_user.id)
        if subject.department_id != mgr.department_id or (staff and staff.department_id != mgr.department_id):
             return jsonify({'error': 'Cannot assign outside department'}), 403

    # Delete existing assignment for this subject (since each subject has only one assigned staff member)
    StaffSubjectAssignment.query.filter_by(class_id=subject.class_id, subject_id=sub_id).delete()

    if staff_id != '':
        new_assign = StaffSubjectAssignment(staff_id=staff_id, class_id=subject.class_id, subject_id=sub_id)
        db.session.add(new_assign)
        db.session.commit()
        return jsonify({'message': f'Subject assigned to {staff.name} successfully'})
    
    db.session.commit()
    return jsonify({'message': 'Subject unassigned successfully'})

# Staff Directory
@app.route('/api/staff', methods=['GET'])
@token_required
def get_staff(current_user, role):
    if role in ['Student', 'CR']:
        return jsonify({'error': 'Students cannot access staff directory'}), 403
    query = Staff.query
    if role in ['HOD', 'AHOD', 'Staff']:
        mgr = db.session.get(Staff, current_user.id)
        query = query.filter_by(department_id=mgr.department_id)

    staff_members = query.all()
    output = []
    for s in staff_members:
        assigned_classes = []
        for a in s.assignments:
             assigned_classes.append({
                  'class_id': a.class_id,
                  'class_name': a.class_.name if a.class_ else None,
                  'course_id': a.class_.course_id if a.class_ else None,
                  'course_name': a.class_.course.name if (a.class_ and a.class_.course) else None
             })
             
        output.append({
            'staff_id': s.staff_id,
            'name': s.name,
            'department_id': s.department_id,
            'department_name': s.department.name,
            'email': s.email,
            'phone': s.phone or '',
            'status': s.status,
            'photo_url': s.photo_url or '',
            'role': s.user.role.name,
            'assigned_classes': assigned_classes
        })
    return jsonify(output)

@app.route('/api/staff', methods=['POST'])
@token_required
def add_staff(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD']:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    if not data or 'staff_id' not in data or 'name' not in data or 'email' not in data:
         return jsonify({'error': 'Missing fields'}), 400

    s_id = data['staff_id'].strip().upper()
    name = data['name'].strip()
    email = data['email'].strip()
    phone = data.get('phone', '')
    status = data.get('status', 'Active')
    photo_url = data.get('photo_url', '')

    if db.session.get(User, s_id):
        return jsonify({'error': 'Staff ID already exists'}), 400

    dept_id = None
    if role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         dept_id = mgr.department_id
    else:
         dept_id = int(data.get('department_id', 0))

    if not dept_id:
         return jsonify({'error': 'Department ID is required'}), 400

    s_role = Role.query.filter_by(name='Staff').first()
    pass_hash = bcrypt.hashpw(b'staff123', bcrypt.gensalt()).decode('utf-8')
    
    new_user = User(id=s_id, name=name, password_hash=pass_hash, role_id=s_role.id)
    db.session.add(new_user)
    db.session.commit()

    staff_profile = Staff(
        staff_id=s_id, name=name, department_id=dept_id,
        email=email, phone=phone, status=status, photo_url=photo_url
    )
    db.session.add(staff_profile)
    db.session.commit()
    return jsonify({'message': 'Staff profile created successfully'}), 201

@app.route('/api/staff/<string:id>', methods=['PUT'])
@token_required
def update_staff(current_user, role, id):
    s_id = id.upper()
    staff = db.session.get(Staff, s_id)
    if not staff:
        return jsonify({'error': 'Staff profile not found'}), 404

    is_self = current_user.id == s_id
    is_auth = role == 'Admin' or (role in ['HOD', 'AHOD'] and staff.department_id == db.session.get(Staff, current_user.id).department_id) or is_self

    if not is_auth:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    if is_self and role not in ['Admin', 'HOD', 'AHOD']:
        if 'name' in data:
             staff.name = data['name'].strip()
             staff.user.name = data['name'].strip()
        if 'email' in data: staff.email = data['email'].strip()
        if 'phone' in data: staff.phone = data['phone'].strip()
        if 'photo_url' in data: staff.photo_url = data['photo_url']
    else:
        if 'name' in data:
             staff.name = data['name'].strip()
             staff.user.name = data['name'].strip()
        if 'email' in data: staff.email = data['email'].strip()
        if 'phone' in data: staff.phone = data['phone'].strip()
        if 'status' in data: staff.status = data['status']
        if 'photo_url' in data: staff.photo_url = data['photo_url']
        if 'department_id' in data and role == 'Admin':
             staff.department_id = int(data['department_id'])

    db.session.commit()
    return jsonify({'message': 'Staff profile updated successfully'})

@app.route('/api/staff/<string:id>', methods=['DELETE'])
@token_required
def delete_staff(current_user, role, id):
    if role != 'Admin':
         return jsonify({'error': 'Admin permissions required'}), 403
    s_id = id.upper()
    staff = db.session.get(Staff, s_id)
    if not staff:
         return jsonify({'error': 'Staff not found'}), 404

    # Remove reference
    dept = Department.query.filter((Department.hod_id == s_id) | (Department.ahod_id == s_id)).first()
    if dept:
         if dept.hod_id == s_id: dept.hod_id = None
         if dept.ahod_id == s_id: dept.ahod_id = None
         db.session.commit()

    db.session.delete(staff)
    user = db.session.get(User, s_id)
    if user:
         db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Staff deleted successfully'})

# Students Directory
@app.route('/api/students', methods=['GET'])
@token_required
def get_students(current_user, role):
    query = Student.query
    class_id = request.args.get('class_id')

    if class_id:
         query = query.filter_by(class_id=class_id)

    if role == 'Student':
         query = query.filter_by(student_id=current_user.id)
    elif role == 'CR':
         stud = db.session.get(Student, current_user.id)
         query = query.filter_by(class_id=stud.class_id)
    elif role == 'Staff':
         fac = db.session.get(Staff, current_user.id)
         query = query.filter_by(department_id=fac.department_id)
    elif role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         query = query.filter_by(department_id=mgr.department_id)

    students = query.all()
    output = []
    for s in students:
        output.append({
            'student_id': s.student_id,
            'name': s.name,
            'class_id': s.class_id,
            'class_name': s.class_.name,
            'course_id': s.class_.course_id if s.class_ else None,
            'course_name': s.class_.course.name if (s.class_ and s.class_.course) else None,
            'department_id': s.department_id,
            'department_name': s.department.name,
            'email': s.email,
            'phone': s.phone or '',
            'status': s.status,
            'photo_url': s.photo_url or '',
            'contact_name': s.contact_name or '',
            'contact_relation': s.contact_relation or '',
            'contact_phone': s.contact_phone or '',
            'role': s.user.role.name
        })
    return jsonify(output)

@app.route('/api/students', methods=['POST'])
@token_required
def add_student(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD', 'Staff', 'CR']:
         return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    if not data or 'student_id' not in data or 'name' not in data or 'email' not in data or 'class_id' not in data:
         return jsonify({'error': 'Missing fields'}), 400

    s_id = data['student_id'].strip().upper()
    name = data['name'].strip()
    email = data['email'].strip()
    class_id = int(data['class_id'])
    phone = data.get('phone', '')
    status = data.get('status', 'Active')
    photo_url = data.get('photo_url', '')
    
    contact_name = data.get('contact_name', '')
    contact_relation = data.get('contact_relation', '')
    contact_phone = data.get('contact_phone', '')

    class_obj = db.session.get(Class, class_id)
    if not class_obj:
         return jsonify({'error': 'Class ID not found'}), 400

    if role in ['HOD', 'AHOD', 'Staff']:
         mgr = db.session.get(Staff, current_user.id)
         if class_obj.department_id != mgr.department_id:
              return jsonify({'error': 'Cannot add students outside your department'}), 403
    elif role == 'CR':
         cr_record = ClassRepresentative.query.filter_by(student_id=current_user.id).first()
         if not cr_record or cr_record.class_id != class_id:
              return jsonify({'error': 'CR can only add students to their own class'}), 403

    if db.session.get(User, s_id):
         return jsonify({'error': 'Student ID already exists'}), 400

    s_role = Role.query.filter_by(name='Student').first()
    pass_hash = bcrypt.hashpw(b'student123', bcrypt.gensalt()).decode('utf-8')
    
    new_user = User(id=s_id, name=name, password_hash=pass_hash, role_id=s_role.id)
    db.session.add(new_user)
    db.session.commit()

    student_profile = Student(
        student_id=s_id, name=name, class_id=class_id, department_id=class_obj.department_id,
        email=email, phone=phone, status=status, photo_url=photo_url,
        contact_name=contact_name, contact_relation=contact_relation, contact_phone=contact_phone
    )
    db.session.add(student_profile)
    db.session.commit()
    return jsonify({'message': 'Student record created successfully'}), 201

@app.route('/api/students/<string:id>', methods=['PUT'])
@token_required
def update_student(current_user, role, id):
    s_id = id.upper()
    student = db.session.get(Student, s_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    is_self = current_user.id == s_id
    is_auth = False
    
    if role == 'Admin': is_auth = True
    elif role in ['HOD', 'AHOD', 'Staff']:
         mgr = db.session.get(Staff, current_user.id)
         if student.department_id == mgr.department_id: is_auth = True
    elif role == 'CR':
         cr = ClassRepresentative.query.filter_by(student_id=current_user.id).first()
         if cr and cr.class_id == student.class_id: is_auth = True
    elif is_self: is_auth = True

    if not is_auth:
         return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    if is_self and role not in ['Admin', 'HOD', 'AHOD', 'Staff', 'CR']:
        if 'phone' in data: student.phone = data['phone'].strip()
        if 'email' in data: student.email = data['email'].strip()
        if 'photo_url' in data: student.photo_url = data['photo_url']
        if 'contact_name' in data: student.contact_name = data['contact_name'].strip()
        if 'contact_relation' in data: student.contact_relation = data['contact_relation'].strip()
        if 'contact_phone' in data: student.contact_phone = data['contact_phone'].strip()
    else:
        if 'name' in data:
             student.name = data['name'].strip()
             student.user.name = data['name'].strip()
        if 'email' in data: student.email = data['email'].strip()
        if 'phone' in data: student.phone = data['phone'].strip()
        if 'status' in data and role != 'CR': student.status = data['status']
        if 'photo_url' in data: student.photo_url = data['photo_url']
        if 'contact_name' in data: student.contact_name = data['contact_name'].strip()
        if 'contact_relation' in data: student.contact_relation = data['contact_relation'].strip()
        if 'contact_phone' in data: student.contact_phone = data['contact_phone'].strip()
        if 'class_id' in data and role != 'CR':
             c_id = int(data['class_id'])
             class_obj = db.session.get(Class, c_id)
             if class_obj:
                  student.class_id = c_id
                  student.department_id = class_obj.department_id

    db.session.commit()
    return jsonify({'message': 'Student record updated successfully'})

@app.route('/api/students/<string:id>', methods=['DELETE'])
@token_required
def delete_student(current_user, role, id):
    if role not in ['Admin', 'HOD', 'AHOD']:
         return jsonify({'error': 'Unauthorized'}), 403
    s_id = id.upper()
    student = db.session.get(Student, s_id)
    if not student:
         return jsonify({'error': 'Student not found'}), 404

    if role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         if student.department_id != mgr.department_id:
              return jsonify({'error': 'Cannot delete students outside department'}), 403

    ClassRepresentative.query.filter_by(student_id=s_id).delete()
    db.session.delete(student)
    user = db.session.get(User, s_id)
    if user:
         db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Student record and login account deleted successfully'})

# --- Attendance Logging APIs ---

# Student Attendance
@app.route('/api/attendance', methods=['POST'])
@token_required
def mark_student_attendance(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD', 'Staff']:
         return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data or 'subject_id' not in data or 'records' not in data:
         return jsonify({'error': 'Missing parameters'}), 400

    sub_id = int(data['subject_id'])
    records = data['records']
    date_str = data.get('date', datetime.date.today().isoformat())
    time_str = data.get('time', datetime.datetime.now().strftime('%H:%M:%S'))

    subject = db.session.get(Subject, sub_id)
    if not subject:
         return jsonify({'error': 'Subject not found'}), 400

    if role == 'Staff':
         assign = StaffSubjectAssignment.query.filter_by(staff_id=current_user.id, subject_id=sub_id).first()
         if not assign:
              return jsonify({'error': 'You are not assigned to teach this subject'}), 403

    db_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    db_time = datetime.datetime.strptime(time_str, '%H:%M:%S').time()

    marked_staff_id = current_user.id
    if role in ['HOD', 'AHOD', 'Admin']:
         assign = StaffSubjectAssignment.query.filter_by(subject_id=sub_id).first()
         marked_staff_id = assign.staff_id if assign else current_user.id

    for r in records:
         stud_id = r['student_id']
         status = r['status']
         
         att = Attendance.query.filter_by(student_id=stud_id, date=db_date, subject_id=sub_id).first()
         if att:
              att.status = status
              att.time = db_time
              att.staff_id = marked_staff_id
         else:
              att = Attendance(
                  student_id=stud_id, date=db_date, time=db_time,
                  subject_id=sub_id, staff_id=marked_staff_id, status=status
              )
              db.session.add(att)

    db.session.commit()
    return jsonify({'message': 'Student attendance sheet recorded successfully'})

@app.route('/api/attendance', methods=['GET'])
@token_required
def get_student_attendance(current_user, role):
    student_id = request.args.get('student_id')
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')

    query = db.session.query(Attendance).join(Student)

    if role == 'Student':
         query = query.filter(Attendance.student_id == current_user.id)
    elif role == 'CR':
         stud = db.session.get(Student, current_user.id)
         query = query.filter(Student.class_id == stud.class_id)
    elif role == 'Staff':
         query = query.filter(Attendance.staff_id == current_user.id)
    elif role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         query = query.filter(Student.department_id == mgr.department_id)

    if student_id: query = query.filter(Attendance.student_id == student_id)
    if class_id: query = query.filter(Student.class_id == class_id)
    if subject_id: query = query.filter(Attendance.subject_id == subject_id)

    records = query.order_by(Attendance.date.desc()).all()
    output = []
    for r in records:
         output.append({
             'student_id': r.student_id,
             'student_name': r.student.name,
             'class': r.student.class_.name,
             'date': r.date.isoformat(),
             'time': r.time.strftime('%H:%M:%S'),
             'subject': r.subject.name,
             'faculty': r.staff.name,
             'status': r.status
         })
    return jsonify(output)

# Staff Attendance
@app.route('/api/attendance/staff', methods=['POST'])
@token_required
def mark_staff_attendance(current_user, role):
    if role not in ['Admin', 'HOD', 'AHOD']:
         return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data or 'staff_id' not in data or 'status' not in data:
         return jsonify({'error': 'Missing required fields'}), 400

    target_staff_id = data['staff_id'].strip().upper()
    status = data['status']
    date_str = data.get('date', datetime.date.today().isoformat())
    check_in_str = data.get('check_in')
    check_out_str = data.get('check_out')

    target_staff = db.session.get(Staff, target_staff_id)
    if not target_staff:
         return jsonify({'error': 'Staff not found'}), 404

    if role in ['HOD', 'AHOD']:
         mgr = db.session.get(Staff, current_user.id)
         if target_staff.department_id != mgr.department_id:
              return jsonify({'error': 'Cannot mark attendance outside department'}), 403

    db_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    db_check_in = datetime.datetime.strptime(check_in_str, '%H:%M:%S').time() if check_in_str else None
    db_check_out = datetime.datetime.strptime(check_out_str, '%H:%M:%S').time() if check_out_str else None

    working_hours = 0.0
    if db_check_in and db_check_out:
         t1 = datetime.datetime.combine(db_date, db_check_in)
         t2 = datetime.datetime.combine(db_date, db_check_out)
         working_hours = round((t2 - t1).total_seconds() / 3600.0, 2)

    att = StaffAttendance.query.filter_by(staff_id=target_staff_id, date=db_date).first()
    if att:
         att.status = status
         att.check_in = db_check_in
         att.check_out = db_check_out
         att.working_hours = working_hours
    else:
         db.session.add(StaffAttendance(
              staff_id=target_staff_id, date=db_date, check_in=db_check_in,
              check_out=db_check_out, status=status, working_hours=working_hours
         ))
    db.session.commit()
    return jsonify({'message': f'Attendance log saved for {target_staff.name}'})

@app.route('/api/attendance/staff', methods=['GET'])
@token_required
def get_staff_attendance(current_user, role):
    staff_id = request.args.get('staff_id')
    query = db.session.query(StaffAttendance).join(Staff)
    
    if role in ['HOD', 'AHOD', 'Staff']:
         mgr = db.session.get(Staff, current_user.id)
         query = query.filter(Staff.department_id == mgr.department_id)
         if role == 'Staff':
              query = query.filter(StaffAttendance.staff_id == current_user.id)

    if staff_id:
         query = query.filter(StaffAttendance.staff_id == staff_id)

    records = query.order_by(StaffAttendance.date.desc()).all()
    output = []
    for r in records:
         output.append({
             'staff_id': r.staff_id,
             'staff_name': r.staff.name,
             'department': r.staff.department.name,
             'date': r.date.isoformat(),
             'check_in': r.check_in.strftime('%H:%M:%S') if r.check_in else '-',
             'check_out': r.check_out.strftime('%H:%M:%S') if r.check_out else '-',
             'status': r.status,
             'working_hours': float(r.working_hours)
         })
    return jsonify(output)

# --- Admin Reset Password ---
@app.route('/api/admin/reset-password', methods=['POST'])
@token_required
def reset_password(current_user, role):
    if role != 'Admin':
        return jsonify({'error': 'Admin permissions required'}), 403
    data = request.get_json()
    if not data or 'user_id' not in data or 'new_password' not in data:
         return jsonify({'error': 'Missing fields'}), 400

    u_id = data['user_id'].strip().upper()
    new_pass = data['new_password']

    user = db.session.get(User, u_id)
    if not user:
         return jsonify({'error': 'User not found'}), 404

    hash_pass = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password_hash = hash_pass
    db.session.commit()
    return jsonify({'message': f'Password for {user.name} reset successfully'})

# --- SPA static routing ---
@app.route('/')
def serve_index():
    return send_from_directory('../frontend/www', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend/www', path)

if __name__ == '__main__':
    with app.app_context():
        seed_database()
    print(f"UINQUE ERP Server running on http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True, use_reloader=False)
