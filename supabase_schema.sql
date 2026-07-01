CREATE TABLE roles (
	id INTEGER NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE users (
	id VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
);

CREATE TABLE departments (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	hod_id VARCHAR(50), 
	ahod_id VARCHAR(50), 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(hod_id) REFERENCES users (id), 
	FOREIGN KEY(ahod_id) REFERENCES users (id)
);

CREATE TABLE courses (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	department_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE classes (
	id INTEGER NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	course_id INTEGER, 
	department_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(course_id) REFERENCES courses (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE subjects (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	class_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT _subject_class_uc UNIQUE (name, class_id), 
	FOREIGN KEY(class_id) REFERENCES classes (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE staff (
	staff_id VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	department_id INTEGER NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	phone VARCHAR(20), 
	status VARCHAR(20), 
	photo_url TEXT, 
	PRIMARY KEY (staff_id), 
	FOREIGN KEY(staff_id) REFERENCES users (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE students (
	student_id VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	class_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	phone VARCHAR(20), 
	status VARCHAR(20), 
	photo_url TEXT, 
	contact_name VARCHAR(100), 
	contact_relation VARCHAR(50), 
	contact_phone VARCHAR(20), 
	PRIMARY KEY (student_id), 
	FOREIGN KEY(student_id) REFERENCES users (id), 
	FOREIGN KEY(class_id) REFERENCES classes (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE staff_subject_assignments (
	id INTEGER NOT NULL, 
	staff_id VARCHAR(50) NOT NULL, 
	class_id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT _class_subject_assignment_uc UNIQUE (class_id, subject_id), 
	FOREIGN KEY(staff_id) REFERENCES staff (staff_id), 
	FOREIGN KEY(class_id) REFERENCES classes (id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
);

CREATE TABLE attendance (
	id INTEGER NOT NULL, 
	student_id VARCHAR(50) NOT NULL, 
	date DATE NOT NULL, 
	time TIME NOT NULL, 
	subject_id INTEGER NOT NULL, 
	staff_id VARCHAR(50) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT _student_attendance_uc UNIQUE (student_id, date, subject_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id), 
	FOREIGN KEY(staff_id) REFERENCES staff (staff_id)
);

CREATE TABLE staff_attendance (
	id INTEGER NOT NULL, 
	staff_id VARCHAR(50) NOT NULL, 
	date DATE NOT NULL, 
	check_in TIME, 
	check_out TIME, 
	status VARCHAR(20) NOT NULL, 
	working_hours NUMERIC(4, 2), 
	PRIMARY KEY (id), 
	FOREIGN KEY(staff_id) REFERENCES staff (staff_id)
);

CREATE TABLE class_representatives (
	class_id INTEGER NOT NULL, 
	student_id VARCHAR(50) NOT NULL, 
	PRIMARY KEY (class_id), 
	FOREIGN KEY(class_id) REFERENCES classes (id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id)
);

CREATE TABLE announcements (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT NOT NULL, 
	date DATE NOT NULL, 
	author_id VARCHAR(50) NOT NULL, 
	department_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES users (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE leave_applications (
	id INTEGER NOT NULL, 
	user_id VARCHAR(50) NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(20), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE timetables (
	id INTEGER NOT NULL, 
	class_id INTEGER NOT NULL, 
	day_of_week VARCHAR(15) NOT NULL, 
	period_1_id INTEGER, 
	period_2_id INTEGER, 
	period_3_id INTEGER, 
	period_4_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(class_id) REFERENCES classes (id), 
	FOREIGN KEY(period_1_id) REFERENCES subjects (id), 
	FOREIGN KEY(period_2_id) REFERENCES subjects (id), 
	FOREIGN KEY(period_3_id) REFERENCES subjects (id), 
	FOREIGN KEY(period_4_id) REFERENCES subjects (id)
);

CREATE TABLE system_settings (
	"key" VARCHAR(50) NOT NULL, 
	value VARCHAR(100) NOT NULL, 
	PRIMARY KEY ("key")
);

