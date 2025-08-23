from flask import Flask, render_template, request, redirect, jsonify
import os
import sqlite3
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz

load_dotenv()

app = Flask(__name__)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)


def convert_to_ist(gmt_time):
    ist_timezone = pytz.timezone('Asia/Kolkata')  
    gmt_time = gmt_time.replace(tzinfo=pytz.utc)  
    ist_time = gmt_time.astimezone(ist_timezone)  
    formatted_time = ist_time.strftime('%Y-%m-%d %I:%M:%S %p IST')  
    return formatted_time

def convert_grade_to_integer(grade):
    grade_mapping = {
        'O': 10,
        'E': 9,
        'A': 8,
        'B': 7,
        'C': 6,
        'D': 5,
        'S': 0,
        'M': 0,
        'F': 0
    }
    return grade_mapping.get(grade, 0)  

def calculate_sgpa(result):
    total_credits = 0
    total_weighted_grades = 0
    
    for row in result:
        credits_parts = [float(part) for part in row[7].split('+')]
        total_credits += sum(credits_parts)
        
        if set(row[8]) <= {'O', 'E', 'A', 'B', 'C', 'D', 'S', 'M', 'F'}:
            grade = convert_grade_to_integer(row[8])
        else:
            grade = float(row[8])
        
        weighted_grade = grade * sum(credits_parts)
        total_weighted_grades += weighted_grade
    
    sgpa = total_weighted_grades / total_credits if total_credits != 0 else 0  
    return sgpa, total_credits

def calculate_cgpa(registration, name):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT Credits, Grade FROM CUTM WHERE (Reg_No = ? OR LOWER(Name) = LOWER(?))", (registration, name))
    rows = cur.fetchall()
    conn.close()

    total_credits = 0
    total_weighted_grades = 0

    for row in rows:
        credits_parts = [float(part) for part in row[0].split('+')]
        
        if set(row[1]) <= {'O', 'E', 'A', 'B', 'C', 'D', 'S', 'M', 'F'}:
            grade = convert_grade_to_integer(row[1])
        else:
            grade = float(row[1])
        
        total_credits += sum(credits_parts)
        weighted_grade = grade * sum(credits_parts)
        total_weighted_grades += weighted_grade

    cgpa = total_weighted_grades / total_credits if total_credits != 0 else 0

    return cgpa

# @app.route('/', methods=['GET', 'POST'])
# def home():
#     try:
#         conn = sqlite3.connect('database.db')
#         cur = conn.cursor()

#         if request.method == 'POST' and request.form.get('registration'):
#             registration = request.form.get('registration')
#             cur.execute("SELECT DISTINCT Sem FROM `CUTM` WHERE Reg_No = ?", (registration,))
#         else:
#             cur.execute("SELECT DISTINCT Sem FROM `CUTM`")
        
#         semesters = [row[0] for row in cur.fetchall()]
#         conn.close()

#         result = None
#         count = 0
#         sgpa = None
#         total_credits = None
#         cgpa = None
#         message = None

#         if request.method == 'POST':
#             name = request.form.get('name')
#             registration = request.form.get('registration')
#             semester = request.form.get('semester')

#             conn = sqlite3.connect('database.db')
#             cur = conn.cursor()

#             cur.execute("SELECT * FROM `CUTM` WHERE (Reg_No = ? OR LOWER(Name) = LOWER(?)) AND Sem = ?", (registration, name, semester))
#             result = cur.fetchall()
#             count = len(result)

#             if count == 0:
#                 message = "No records found for the entered name or registration number."

#             if result:
#                 sgpa, total_credits = calculate_sgpa(result)

#             cgpa = calculate_cgpa(registration, name)
#             conn.close()

#             current_time_utc = datetime.utcnow()
#             current_time_ist = convert_to_ist(current_time_utc)

#             client = MongoClient(MONGO_URI)
#             db = client.get_database('cutm')
#             collection = db.get_collection('userInput')

#             data = {
#                 'registration': registration,
#                 'semester': semester,
#                 'time': current_time_ist
#             }

#             collection.insert_one(data)

#             return render_template('display.html', result=result, count=count, sgpa=sgpa, total_credits=total_credits, cgpa=cgpa, message=message, selected_semester=semester, semesters=semesters)

#         return render_template('index.html', semesters=semesters)
#     except Exception as e:
#         return render_template('index.html', error=str(e))

















import pandas as pd
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/update_data', methods=['GET', 'POST'])
def update_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('update_data.html', error="No file part")
        file = request.files['file']
        if file.filename == '':
            return render_template('update_data.html', error="No selected file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Read file with pandas
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)

            conn = sqlite3.connect('database.db')
            cur = conn.cursor()

            for _, row in df.iterrows():
                #reg_no = str(row['Reg_No']).strip()
                reg_no = str(row.get('Reg_No') or row.get('Registration No.')).strip()
                subject_code = str(row.get('Subject_Code') or row.get('Subject Code')).strip()
              #  subject_code = str(row['Subject_Code']).strip()
               
                grade = str(row['Grade']).strip()
               # credits = str(row['Credits']).strip()
                credits= str(row.get('Credits') or row.get('Credit')).strip()

                name = str(row['Name']).strip() if 'Name' in df.columns else None
                sem = str(row['Sem']).strip() if 'Sem' in df.columns else None# Ask once if column is missing
 
                 

                subject_name = str(row['Subject_Name']).strip() if 'Subject_Name' in df.columns else None

                # Check if record exists
                cur.execute("SELECT * FROM CUTM WHERE Reg_No=? AND Subject_Code=?", (reg_no, subject_code))
                existing = cur.fetchone()

                if existing:
                    # Update grade if exists
                    cur.execute("UPDATE CUTM SET Grade=? WHERE Reg_No=? AND Subject_Code=?", 
                                (grade, reg_no, subject_code))
                else:
                    # Insert new row
                    cur.execute("""
                        INSERT INTO CUTM (Reg_No, Name, Sem, Subject_Code, Subject_Name, Credits, Grade)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (reg_no, name, sem, subject_code, subject_name, credits, grade))

            conn.commit()
            conn.close()

            return render_template('update_data.html', success="Data updated successfully!")

    return render_template('update_data.html')


@app.route('/view_data', methods=['GET', 'POST'])
def view_data():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if request.method == 'POST':
        reg_no = request.form.get('reg_no')
        subject_code = request.form.get('subject_code')
        new_grade = request.form.get('new_grade')
        if reg_no and subject_code and new_grade:
            cur.execute("UPDATE CUTM SET Grade=? WHERE Reg_No=? AND Subject_Code=?", 
                        (new_grade, reg_no, subject_code))
            conn.commit()

    cur.execute("SELECT Reg_No, Name, Sem, Subject_Code, Subject_Name, Credits, Grade FROM CUTM")
    rows = cur.fetchall()
    conn.close()

    return render_template('view_data.html', rows=rows)












@app.route('/backlog', methods=['GET', 'POST'])
def backlog():
    try:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        
        result = []
        count = 0
        message = None
        search_type = None  # To distinguish if search is by registration or subject

        if request.method == 'POST':
            reg_no = request.form.get('registration')
            subject_name = request.form.get('subject')

            if reg_no:  # Search by registration number
                search_type = 'registration'
                cur.execute("""
                    SELECT Sem, Subject_Code, Subject_Name, Credits, Grade 
                    FROM CUTM 
                    WHERE Reg_No = ? AND Grade IN ('F','M','S')
                """, (reg_no,))
                result = cur.fetchall()
                count = len(result)
                if count == 0:
                    message = f"No backlog found for registration number {reg_no}."

            elif subject_name:  # Search by subject name
                search_type = 'subject'
                cur.execute("""
                    SELECT Reg_No, Name, Sem, Subject_Code, Subject_Name , Grade 
                    FROM CUTM 
                    WHERE Subject_Name LIKE ? AND Grade IN ('F','M','S')
                """, (f"%{subject_name}%",))
                result = cur.fetchall()
                count = len(result)
                if count == 0:
                    message = f"No students found with backlog in subject '{subject_name}'."
            else:
                message = "Please enter a registration number or subject name to search."

        conn.close()
        return render_template('backlog.html', result=result, count=count, message=message, search_type=search_type)

    except Exception as e:
        return render_template('backlog.html', error=str(e))




















@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        if request.method == 'POST' and request.form.get('registration'):
            registration = request.form.get('registration')
            cur.execute("SELECT DISTINCT Sem FROM `CUTM` WHERE Reg_No = ?", (registration,))
        else:
            cur.execute("SELECT DISTINCT Sem FROM `CUTM`")
        
        semesters = [row[0] for row in cur.fetchall()]
        conn.close()

        result = None
        count = 0
        sgpa = None
        total_credits = None
        cgpa = None
        total_all_semester_credits = 0  # To store total credits from all semesters
        message = None

        if request.method == 'POST':
            name = request.form.get('name')
            registration = request.form.get('registration')
            semester = request.form.get('semester')

            conn = sqlite3.connect('database.db')
            cur = conn.cursor()

            cur.execute("SELECT * FROM `CUTM` WHERE (Reg_No = ? OR LOWER(Name) = LOWER(?)) AND Sem = ?", (registration, name, semester))
            result = cur.fetchall()
            count = len(result)

            if count == 0:
                message = "No records found for the entered name or registration number."

            if result:
                sgpa, total_credits = calculate_sgpa(result)

            # Calculate total credits across all semesters
            cur.execute("SELECT Credits FROM `CUTM` WHERE Reg_No = ?", (registration,))
            all_credits = cur.fetchall()
            total_all_semester_credits = sum([sum([float(part) for part in row[0].split('+')]) for row in all_credits])

            cgpa = calculate_cgpa(registration, name)
            conn.close()

            current_time_utc = datetime.utcnow()
            current_time_ist = convert_to_ist(current_time_utc)

            client = MongoClient(MONGO_URI)
            db = client.get_database('cutm')
            collection = db.get_collection('userInput')

            data = {
                'registration': registration,
                'semester': semester,
                'time': current_time_ist
            }

            collection.insert_one(data)

            return render_template('display.html', result=result, count=count, sgpa=sgpa, total_credits=total_credits, cgpa=cgpa, total_all_semester_credits=total_all_semester_credits, message=message, selected_semester=semester, semesters=semesters)

        return render_template('index.html', semesters=semesters)
    except Exception as e:
        return render_template('index.html', error=str(e))
    











    

@app.route('/semesters', methods=['POST'])
def get_semesters():
    try:
        registration = request.form.get('registration')
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT Sem FROM `CUTM` WHERE Reg_No = ?", (registration,))
        semesters = [row[0] for row in cur.fetchall()]
        conn.close()
        return jsonify(semesters=semesters)
    except Exception as e:
        return jsonify(error=str(e))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return redirect('/admin/panel')
        else:
            error = 'Invalid username or password'
            return render_template('admin_login.html', error=error)
    return render_template('admin_login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin/panel')
def admin_panel():
    return render_template('admin_panel.html')

if __name__ == '__main__':
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT Sem FROM CUTM")
    semesters = [row[0] for row in cur.fetchall()]

    conn.close()

    app.run(port=5000, host="0.0.0.0", debug=True)
