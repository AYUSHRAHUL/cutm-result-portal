from flask import Flask, render_template, request, redirect, jsonify
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz
import pandas as pd
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client.get_database("cutm")
cutm_collection = db.get_collection("CUTM")
user_input_collection = db.get_collection("userInput")

# ---------------- Utilities ----------------
def convert_to_ist(gmt_time):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    gmt_time = gmt_time.replace(tzinfo=pytz.utc)
    return gmt_time.astimezone(ist_timezone).strftime('%Y-%m-%d %I:%M:%S %p IST')

def convert_grade_to_integer(grade):
    grade_mapping = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'S': 0, 'M': 0, 'F': 0}
    return grade_mapping.get(grade, 0)

def calculate_sgpa(result):
    total_credits, total_weighted_grades = 0, 0
    for row in result:
        credits_parts = [float(part) for part in row["Credits"].split('+')]
        grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
        total_credits += sum(credits_parts)
        total_weighted_grades += grade * sum(credits_parts)
    sgpa = total_weighted_grades / total_credits if total_credits else 0
    return sgpa, total_credits

def calculate_cgpa(registration, name):
    rows = list(cutm_collection.find({"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Credits": 1, "Grade": 1}))
    total_credits, total_weighted_grades = 0, 0
    for row in rows:
        credits_parts = [float(part) for part in row["Credits"].split('+')]
        grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
        total_credits += sum(credits_parts)
        total_weighted_grades += grade * sum(credits_parts)
    cgpa = total_weighted_grades / total_credits if total_credits else 0
    return cgpa

# ---------------- Home ----------------
@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        if request.method == 'POST' and request.form.get('registration'):
            registration = request.form.get('registration')
            semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
        else:
            semesters = sorted({doc["Sem"] for doc in cutm_collection.find({}, {"Sem": 1})})

        result, count, sgpa, total_credits, cgpa, total_all_semester_credits, message = [], 0, None, None, None, 0, None

        if request.method == 'POST':
            name = request.form.get('name')
            registration = request.form.get('registration')
            semester = request.form.get('semester')

            result = list(cutm_collection.find(
                {"$and": [{"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Sem": semester}]},
                {"_id": 0}
            ))
            count = len(result)

            if count == 0:
                message = "No records found for the entered name or registration number."

            if result:
                sgpa, total_credits = calculate_sgpa(result)

            all_credits = cutm_collection.find({"Reg_No": registration}, {"Credits": 1, "_id": 0})
            total_all_semester_credits = sum(sum(float(part) for part in row["Credits"].split('+')) for row in all_credits)

            cgpa = calculate_cgpa(registration, name)

            # Log search
            user_input_collection.insert_one({
                "registration": registration,
                "semester": semester,
                "time": convert_to_ist(datetime.utcnow())
            })

            return render_template('display.html', result=result, count=count, sgpa=sgpa, total_credits=total_credits,
                                   cgpa=cgpa, total_all_semester_credits=total_all_semester_credits, message=message,
                                   selected_semester=semester, semesters=semesters)

        return render_template('index.html', semesters=semesters)
    except Exception as e:
        return render_template('index.html', error=str(e))

# ---------------- Get Semesters ----------------
@app.route('/semesters', methods=['POST'])
def get_semesters():
    try:
        registration = request.form.get('registration')
        semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
        return jsonify(semesters=semesters)
    except Exception as e:
        return jsonify(error=str(e))

# ---------------- Update Data ----------------
# UPLOAD_FOLDER = 'uploads'
# ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/update_data', methods=['GET', 'POST'])
# def update_data():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             return render_template('update_data.html', error="No file part")
#         file = request.files['file']
#         if file.filename == '':
#             return render_template('update_data.html', error="No selected file")
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(filepath)

#             # Load CSV or Excel
#             df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)

#             for _, row in df.iterrows():
#                 reg_no = str(row.get('Reg_No') or row.get('Registration No.')).strip()
#                 subject_code = str(row.get('Subject_Code') or row.get('Subject Code')).strip()
#                 subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
#                 name = str(row.get('Name') or "").strip()
#                 sem = str(row.get('Sem') or "").strip()
#                 credits = str(row.get('Credits') or row.get('Credit') or "").strip()
#                 grade = str(row.get('Grade') or row.get('Grade Point') or "").strip()
#                 subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()

#                 # Convert sem number to "Sem X"
#                 sem_value = f"Sem {sem}" if sem.isdigit() else sem

#                 # Upsert: update grade if exists, else insert new record with full data
#                 cutm_collection.update_one(
#                     {"Reg_No": reg_no, "Subject_Code": subject_code},
#                     {
#                         "$set": {"Grade": grade},   # always update grade
#                         "$setOnInsert": {           # insert full data if not exists
                            
#                             "Reg_No": reg_no,
#                             "Name": name,
#                             "Sem": sem_value,
#                             "Subject_Code": subject_code,
#                             "Subject_Name": subject_name,
#                             "Subject_Type": subject_type,
#                             "credits": credits
#                         }
#                     },
#                     upsert=True
#                 )

#             return render_template('update_data.html', success="Data updated successfully!")

#     return render_template('update_data.html')



UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

            # Load CSV or Excel
            df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)

            for _, row in df.iterrows():
                reg_no = str(row.get('Reg_No') or row.get('Registration No.')).strip()
                subject_code = str(row.get('Subject_Code') or row.get('Subject Code')).strip()
                subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
                name = str(row.get('Name') or "").strip()
                sem = str(row.get('Sem') or "").strip()
                credits = str(row.get('Credits') or row.get('Credit') or "").strip()
                grade = str(row.get('Grade') or row.get('Grade Point') or "").strip()
                subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()

                sem_value = f"Sem {sem}" if sem.isdigit() else sem

                # Upsert: update grade if exists, else insert full record
                cutm_collection.update_one(
                    {"Reg_No": reg_no, "Subject_Code": subject_code},
                    {
                        "$set": {"Grade": grade,    # update grade
                                 "Name": name,
                                 "Sem": sem_value,
                                 "Subject_Name": subject_name,
                                 "Subject_Type": subject_type,
                                 "credits": credits
                                }
                    },
                    upsert=True
                )

            return render_template('update_data.html', success="Data updated successfully!")

    return render_template('update_data.html')



# ---------------- View Data ----------------
@app.route('/view_data', methods=['GET', 'POST'])
def view_data():
    if request.method == 'POST':
        reg_no = request.form.get('reg_no')
        subject_code = request.form.get('subject_code')
        new_grade = request.form.get('new_grade')
        if reg_no and subject_code and new_grade:
            cutm_collection.update_one({"Reg_No": reg_no, "Subject_Code": subject_code}, {"$set": {"Grade": new_grade}})

    rows = list(cutm_collection.find({}, {"_id": 0}))
    return render_template('view_data.html', rows=rows)

# ---------------- Backlog ----------------
@app.route('/backlog', methods=['GET', 'POST'])
def backlog():
    try:
        result, count, message, search_type = [], 0, None, None
        if request.method == 'POST':
            reg_no = request.form.get('registration')
            subject_name = request.form.get('subject')

            if reg_no:
                search_type = 'registration'
                result = list(cutm_collection.find({"Reg_No": reg_no, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
                count = len(result)
                if count == 0:
                    message = f"No backlog found for registration number {reg_no}."
            elif subject_name:
                search_type = 'subject'
                result = list(cutm_collection.find({"Subject_Name": {"$regex": subject_name, "$options": "i"}, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
                count = len(result)
                if count == 0:
                    message = f"No students found with backlog in subject '{subject_name}'."
            else:
                message = "Please enter a registration number or subject name to search."

        return render_template('backlog.html', result=result, count=count, message=message, search_type=search_type)
    except Exception as e:
        return render_template('backlog.html', error=str(e))

# ---------------- Admin ----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return redirect('/admin/panel')
        else:
            return render_template('admin_login.html', error="Invalid username or password")
    return render_template('admin_login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin/panel')
def admin_panel():
    return render_template('admin_panel.html')

# ---------------- Run ----------------
if __name__ == '__main__':
    app.run(port=5000, host="0.0.0.0", debug=True)
