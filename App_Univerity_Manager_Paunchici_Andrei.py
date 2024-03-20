import sqlite3
import hashlib
import os

# Constants for application settings
MAX_ATTENDANCE = 20
MAX_MARKS = 100

# Establish database connection and create cursor
conn = sqlite3.connect("students.db")
cur = conn.cursor()

# Create tables for students, courses, and course enrollments if they do not exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        name TEXT, 
        roll INTEGER PRIMARY KEY AUTOINCREMENT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_name TEXT PRIMARY KEY, 
        teacher TEXT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS course_enrollments (
        roll INTEGER,
        course_name TEXT,
        marks INTEGER DEFAULT 0, 
        attendance INTEGER DEFAULT 0,
        FOREIGN KEY(roll) REFERENCES students(roll),
        FOREIGN KEY(course_name) REFERENCES courses(course_name)
    )
""")

# Student class to handle student-related operations
class Student:
    def __init__(self, name):
        self.name = name
        self.roll = None

    def add_to_db(self):
        cur.execute("INSERT INTO students (name) VALUES (?)", (self.name,))
        conn.commit()
        self.roll = cur.lastrowid

# Course class to handle course-related operations
class Course:
    @staticmethod
    def update_course(roll, course_name, marks, attendance):
        cur.execute("""
            UPDATE course_enrollments 
            SET marks = ?, attendance = ?
            WHERE roll = ? AND course_name = ?
        """, (marks, attendance, roll, course_name))
        conn.commit()

    @staticmethod
    def create_course(course_name, teacher):
        cur.execute("INSERT INTO courses (course_name, teacher) VALUES (?, ?)", 
                    (course_name, teacher))
        conn.commit()

# Base User class for common user functionalities
class User:
    def __init__(self, username, password):
        self.username = username
        self.hashed_password = self.hash_password(password)

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, filename):
        with open(filename, 'r') as file:
            for line in file:
                user, pwd = line.strip().split(':')
                if user == self.username and pwd == self.hashed_password:
                    return True
            return False

# StudentUser class for student-specific functionalities
class StudentUser(User):
    def __init__(self, username, password):
        super().__init__(username, password)

    def view_enrolled_courses(self):
        while True:
            cur.execute("""
                SELECT course_name 
                FROM course_enrollments 
                WHERE roll = (SELECT roll FROM students WHERE name = ?)
            """, (self.username,))
            courses = cur.fetchall()

            if not courses:
                print("You are not enrolled in any courses.")
                return

            print("Enrolled Courses:")
            for i, course in enumerate(courses, start=1):
                print(f"{i}. {course[0]}")
            print(f"{len(courses) + 1}. Exit")

            try:
                choice = int(input("Select a course to view details or 'Exit' (Enter the number): "))
                if choice == len(courses) + 1:
                    break
                elif 1 <= choice <= len(courses):
                    course_name = courses[choice - 1][0]
                    self.view_course_details(course_name)
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def view_course_details(self, course_name):
        cur.execute("""
            SELECT marks, attendance
            FROM course_enrollments
            WHERE roll = (SELECT roll FROM students WHERE name = ?) AND course_name = ?
        """, (self.username, course_name))
        details = cur.fetchone()
        if details:
            marks, attendance = details
            print(f"\nCourse: {course_name}\nMarks: {marks}\nAttendance: {attendance}")
        else:
            print("No details available for this course.")

# TeacherUser class for teacher-specific functionalities
class TeacherUser(User):
    def __init__(self, username, password):
        super().__init__(username, password)

    def view_and_modify_courses(self):
        cur.execute("SELECT course_name FROM courses WHERE teacher = ?", (self.username,))
        courses = cur.fetchall()

        if not courses:
            print("You have no courses.")
            return

        print("Your Courses:")
        for i, course in enumerate(courses, start=1):
            print(f"{i}. {course[0]}")

        course_choice = int(input("Select a course to view students, or 0 to return: "))
        if course_choice == 0:
            return

        course_name = courses[course_choice - 1][0]
        cur.execute("SELECT students.name, students.roll FROM students JOIN course_enrollments ON students.roll = course_enrollments.roll WHERE course_enrollments.course_name = ?", (course_name,))
        students = cur.fetchall()

        if not students:
            print("No students enrolled in this course.")
            return

        print("\nStudents in this course:")
        for i, student in enumerate(students, start=1):
            print(f"{i}. {student[0]} (Roll: {student[1]})")

        student_choice = int(input("Select a student to modify grades and attendance, or 0 to return: "))
        if student_choice == 0:
            return

        selected_student = students[student_choice - 1]
        student_roll = selected_student[1]
        marks = int(input(f"Enter new marks (0 to {MAX_MARKS}): "))
        attendance = int(input(f"Enter new attendance (0 to {MAX_ATTENDANCE}): "))
        Course.update_course(student_roll, course_name, marks, attendance)
        print("Course updated successfully.")

    def create_course(self):
        course_name = input("Enter the new course name: ")
        Course.create_course(course_name, self.username)
        print("Course created successfully.")

    def add_student_to_course(self):
        student_name = input("Enter the student's name to enroll: ")
        cur.execute("SELECT roll FROM students WHERE name = ?", (student_name,))
        result = cur.fetchone()
        
        if not result:
            print(f"No student found with the name '{student_name}'. Adding new student.")
            new_student = Student(student_name)
            new_student.add_to_db()
            roll = new_student.roll
        else:
            roll = result[0]

        course_name = input("Enter course name to enroll the student: ")
        # Check if the student is already enrolled in the course
        cur.execute("""
            SELECT * FROM course_enrollments 
            WHERE roll = ? AND course_name = ?
        """, (roll, course_name))
        if cur.fetchone():
            print(f"Student '{student_name}' is already enrolled in {course_name}.")
            return

        cur.execute("INSERT INTO course_enrollments (roll, course_name) VALUES (?, ?)", (roll, course_name))
        conn.commit()
        print(f"Student '{student_name}' enrolled in {course_name}.")

# Check if user already exists in the database
def user_exists(username, filename):
    with open(filename, 'r') as file:
        for line in file:
            existing_username, _ = line.strip().split(':')
            if existing_username == username:
                return True
    return False

# Register a new user
def register_user():
    user_type = input("Register as a Student or Teacher? (1 for Student, 2 for Teacher): ")
    filename = "Students.txt" if user_type == "1" else "VIP.txt"

    username = input("Enter new username (your name): ")
    if user_exists(username, filename):
        print("Username already exists. Please choose a different username.")
        return

    password = input("Enter new password: ")
    hashed_password = User.hash_password(password)

    with open(filename, 'a') as file:
        file.write(f"{username}:{hashed_password}\n")
    print("Registration successful.")

# Log in a user
def login():
    print("Welcome to the Student Management System")
    user_type = input("Are you a Student or Teacher? (1 for Student, 2 for Teacher): ")
    username = input("Username: ")
    password = input("Password: ")
    user_class = StudentUser if user_type == "1" else TeacherUser
    user = user_class(username, password)
    filename = "Students.txt" if user_type == "1" else "VIP.txt"

    if user.authenticate(filename):
        return user
    else:
        print("Invalid credentials or user type.")
        return None

# Main function to run the program
def main():
    for filename in ["VIP.txt", "Students.txt"]:
        if not os.path.exists(filename):
            with open(filename, 'w'):
                pass

    while True:
        print("\n1. Login\n2. Register\n3. Exit")
        action = input("Choose an option (1-3): ")

        if action == "3":
            break
        elif action == "2":
            register_user()
        elif action == "1":
            user = login()
            if user:
                if isinstance(user, TeacherUser):
                    while True:
                        print("\n1. View and Modify Courses\n2. Create Course\n3. Add Student to Course\n4. Back to Main Menu")
                        choice = input("Choose an option (1-4): ")
                        if choice == '1':
                            user.view_and_modify_courses()
                        elif choice == '2':
                            user.create_course()
                        elif choice == '3':
                            user.add_student_to_course()
                        elif choice == '4':
                            break
                elif isinstance(user, StudentUser):
                    user.view_enrolled_courses()
                    input("Press any key to return to main menu...")

if __name__ == "__main__":
    main()

# Close the database connection
conn.close()
