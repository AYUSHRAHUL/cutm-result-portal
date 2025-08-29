# from flask import Flask, render_template, request, redirect, jsonify
# import os
# from dotenv import load_dotenv
# from pymongo import MongoClient
# from datetime import datetime
# import pytz
# import pandas as pd
# from werkzeug.utils import secure_filename

# load_dotenv()

# app = Flask(__name__)

# ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
# ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
# MONGO_URI = os.getenv('MONGO_URI')

# client = MongoClient(MONGO_URI)
# db = client.get_database("cutm")
# cutm_collection = db.get_collection("CUTM")
# user_input_collection = db.get_collection("userInput")

# # ---------------- Utilities ----------------
# def convert_to_ist(gmt_time):
#     ist_timezone = pytz.timezone('Asia/Kolkata')
#     gmt_time = gmt_time.replace(tzinfo=pytz.utc)
#     return gmt_time.astimezone(ist_timezone).strftime('%Y-%m-%d %I:%M:%S %p IST')

# def convert_grade_to_integer(grade):
#     grade_mapping = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'S': 0, 'M': 0, 'F': 0}
#     return grade_mapping.get(grade, 0)

# def calculate_sgpa(result):
#     total_credits, total_weighted_grades = 0, 0
#     for row in result:
#         credits_parts = [float(part) for part in row["Credits"].split('+')]
#         grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
#         total_credits += sum(credits_parts)
#         total_weighted_grades += grade * sum(credits_parts)
#     sgpa = total_weighted_grades / total_credits if total_credits else 0
#     return sgpa, total_credits

# def calculate_cgpa(registration, name):
#     rows = list(cutm_collection.find({"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Credits": 1, "Grade": 1}))
#     total_credits, total_weighted_grades = 0, 0
#     for row in rows:
#         credits_parts = [float(part) for part in row["Credits"].split('+')]
#         grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
#         total_credits += sum(credits_parts)
#         total_weighted_grades += grade * sum(credits_parts)
#     cgpa = total_weighted_grades / total_credits if total_credits else 0
#     return cgpa

# # ---------------- Home ----------------
# @app.route('/', methods=['GET', 'POST'])
# def home():
#     try:
#         if request.method == 'POST' and request.form.get('registration'):
#             registration = request.form.get('registration')
#             semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
#         else:
#             semesters = sorted({doc["Sem"] for doc in cutm_collection.find({}, {"Sem": 1})})

#         result, count, sgpa, total_credits, cgpa, total_all_semester_credits, message = [], 0, None, None, None, 0, None

#         if request.method == 'POST':
#             name = request.form.get('name')
#             registration = request.form.get('registration')
#             semester = request.form.get('semester')

#             result = list(cutm_collection.find(
#                 {"$and": [{"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Sem": semester}]},
#                 {"_id": 0}
#             ))
#             count = len(result)

#             if count == 0:
#                 message = "No records found for the entered name or registration number."

#             if result:
#                 sgpa, total_credits = calculate_sgpa(result)

#             all_credits = cutm_collection.find({"Reg_No": registration}, {"Credits": 1, "_id": 0})
#             total_all_semester_credits = sum(sum(float(part) for part in row["Credits"].split('+')) for row in all_credits)

#             cgpa = calculate_cgpa(registration, name)

#             # Log search
#             user_input_collection.insert_one({
#                 "registration": registration,
#                 "semester": semester,
#                 "time": convert_to_ist(datetime.utcnow())
#             })

#             return render_template('display.html', result=result, count=count, sgpa=sgpa, total_credits=total_credits,
#                                    cgpa=cgpa, total_all_semester_credits=total_all_semester_credits, message=message,
#                                    selected_semester=semester, semesters=semesters)

#         return render_template('index.html', semesters=semesters)
#     except Exception as e:
#         return render_template('index.html', error=str(e))

# # ---------------- Get Semesters ----------------
# @app.route('/semesters', methods=['POST'])
# def get_semesters():
#     try:
#         registration = request.form.get('registration')
#         semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
#         return jsonify(semesters=semesters)
#     except Exception as e:
#         return jsonify(error=str(e))

# # ---------------- Update Data ----------------
# # UPLOAD_FOLDER = 'uploads'
# # ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
# # app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# # os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# # def allowed_file(filename):
# #     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # @app.route('/update_data', methods=['GET', 'POST'])
# # def update_data():
# #     if request.method == 'POST':
# #         if 'file' not in request.files:
# #             return render_template('update_data.html', error="No file part")
# #         file = request.files['file']
# #         if file.filename == '':
# #             return render_template('update_data.html', error="No selected file")
# #         if file and allowed_file(file.filename):
# #             filename = secure_filename(file.filename)
# #             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
# #             file.save(filepath)

# #             # Load CSV or Excel
# #             df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)

# #             for _, row in df.iterrows():
# #                 reg_no = str(row.get('Reg_No') or row.get('Registration No.')).strip()
# #                 subject_code = str(row.get('Subject_Code') or row.get('Subject Code')).strip()
# #                 subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
# #                 name = str(row.get('Name') or "").strip()
# #                 sem = str(row.get('Sem') or "").strip()
# #                 credits = str(row.get('Credits') or row.get('Credit') or "").strip()
# #                 grade = str(row.get('Grade') or row.get('Grade Point') or "").strip()
# #                 subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()

# #                 # Convert sem number to "Sem X"
# #                 sem_value = f"Sem {sem}" if sem.isdigit() else sem

# #                 # Upsert: update grade if exists, else insert new record with full data
# #                 cutm_collection.update_one(
# #                     {"Reg_No": reg_no, "Subject_Code": subject_code},
# #                     {
# #                         "$set": {"Grade": grade},   # always update grade
# #                         "$setOnInsert": {           # insert full data if not exists
                            
# #                             "Reg_No": reg_no,
# #                             "Name": name,
# #                             "Sem": sem_value,
# #                             "Subject_Code": subject_code,
# #                             "Subject_Name": subject_name,
# #                             "Subject_Type": subject_type,
# #                             "credits": credits
# #                         }
# #                     },
# #                     upsert=True
# #                 )

# #             return render_template('update_data.html', success="Data updated successfully!")

# #     return render_template('update_data.html')
# UPLOAD_FOLDER = 'uploads'
# ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/update_data', methods=['GET', 'POST'])
# def update_data():
#     if request.method == 'POST':
#         if 'files' not in request.files:
#             return render_template('update_data.html', error="No file part")
        
#         files = request.files.getlist('files')
#         if not files or all(f.filename == '' for f in files):
#             return render_template('update_data.html', error="No selected files")
        
#         updated_count = 0
#         inserted_count = 0

#         for file in files:
#             if file and allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 file.save(filepath)

#                 # Load CSV or Excel
#                 if filename.endswith('.csv'):
#                     df = pd.read_csv(filepath)
#                 else:
#                     df = pd.read_excel(filepath)

#                 for _, row in df.iterrows():
#                     # Normalize all keys
#                     reg_no = str(row.get('Reg_No') or row.get('Registration No.') or "").strip().upper()
#                     subject_code = str(row.get('Subject_Code') or row.get('Subject Code') or "").strip().upper()
#                     subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
#                     name = str(row.get('Name') or "").strip()
#                     sem = str(row.get('Sem') or "").strip()
#                     credits = str(row.get('Credits') or row.get('Credit') or "").strip()
#                     grade = str(row.get('Grade') or row.get('Grade Point') or "").strip().upper()
#                     subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()
#                     sem_value = f"Sem {sem}" if sem.isdigit() else sem

#                     if not reg_no or not subject_code:
#                         continue  # skip invalid rows

#                     existing_record = cutm_collection.find_one({
#                         "Reg_No": reg_no,
#                         "Subject_Code": subject_code
#                     })

#                     if existing_record:
#                         # Update only if existing grade in DB is F, S, or M
#                         if existing_record.get("Grade") in {'F', 'S', 'M'}:
#                             cutm_collection.update_one(
#                                 {"Reg_No": reg_no, "Subject_Code": subject_code},
#                                 {"$set": {"Grade": grade}}
#                             )
#                             updated_count += 1
#                             print(f"Updated {reg_no}-{subject_code} from {existing_record.get('Grade')} to {grade}")
#                     else:
#                         # Insert new record with any grade
#                         cutm_collection.insert_one({
#                             "Reg_No": reg_no,
#                             "Subject_Code": subject_code,
#                             "Grade": grade,
#                             "Name": name,
#                             "Sem": sem_value,
#                             "Subject_Name": subject_name,
#                             "Subject_Type": subject_type,
#                             "credits": credits
#                         })
#                         inserted_count += 1
#                         print(f"Inserted new record {reg_no}-{subject_code} with grade {grade}")

#         message = f"All files processed successfully! Updated: {updated_count}, Inserted: {inserted_count}"
#         return render_template('update_data.html', success=message)

#     return render_template('update_data.html')



# # ---------------- View Data ----------------
# @app.route('/view_data', methods=['GET', 'POST'])
# def view_data():
#     if request.method == 'POST':
#         reg_no = request.form.get('reg_no')
#         subject_code = request.form.get('subject_code')
#         new_grade = request.form.get('new_grade')
#         if reg_no and subject_code and new_grade:
#             cutm_collection.update_one({"Reg_No": reg_no, "Subject_Code": subject_code}, {"$set": {"Grade": new_grade}})

#     rows = list(cutm_collection.find({}, {"_id": 0}))
#     return render_template('view_data.html', rows=rows)

# # ---------------- Backlog ----------------
# @app.route('/backlog', methods=['GET', 'POST'])
# def backlog():
#     try:
#         result, count, message, search_type = [], 0, None, None
#         if request.method == 'POST':
#             reg_no = request.form.get('registration')
#             subject_name = request.form.get('subject')

#             if reg_no:
#                 search_type = 'registration'
#                 result = list(cutm_collection.find({"Reg_No": reg_no, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
#                 count = len(result)
#                 if count == 0:
#                     message = f"No backlog found for registration number {reg_no}."
#             elif subject_name:
#                 search_type = 'subject'
#                 result = list(cutm_collection.find({"Subject_Name": {"$regex": subject_name, "$options": "i"}, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
#                 count = len(result)
#                 if count == 0:
#                     message = f"No students found with backlog in subject '{subject_name}'."
#             else:
#                 message = "Please enter a registration number or subject name to search."

#         return render_template('backlog.html', result=result, count=count, message=message, search_type=search_type)
#     except Exception as e:
#         return render_template('backlog.html', error=str(e))

# # ---------------- Admin ----------------
# @app.route('/admin/login', methods=['GET', 'POST'])
# def admin_login():
#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
#         if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
#             return redirect('/admin/panel')
#         else:
#             return render_template('admin_login.html', error="Invalid username or password")
#     return render_template('admin_login.html')

# @app.route('/about')
# def about():
#     return render_template('about.html')

# @app.route('/admin/panel')
# def admin_panel():
#     return render_template('admin_panel.html')

# # ---------------- Run ----------------
# if __name__ == '__main__':
#     app.run(port=5000, host="0.0.0.0", debug=True)















# from flask import Flask, render_template, request, redirect, jsonify
# import os
# from dotenv import load_dotenv
# from pymongo import MongoClient
# from datetime import datetime
# import pytz
# import pandas as pd
# from werkzeug.utils import secure_filename
# import io  # Added for in-memory file reading

# load_dotenv()

# app = Flask(__name__)

# ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
# ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
# MONGO_URI = os.getenv('MONGO_URI')

# client = MongoClient(MONGO_URI)
# db = client.get_database("cutm")
# cutm_collection = db.get_collection("CUTM")
# user_input_collection = db.get_collection("userInput")


# # ---------------- Utilities ----------------
# def convert_to_ist(gmt_time):
#     ist_timezone = pytz.timezone('Asia/Kolkata')
#     gmt_time = gmt_time.replace(tzinfo=pytz.utc)
#     return gmt_time.astimezone(ist_timezone).strftime('%Y-%m-%d %I:%M:%S %p IST')


# def convert_grade_to_integer(grade):
#     grade_mapping = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'S': 0, 'M': 0, 'F': 0}
#     return grade_mapping.get(grade, 0)


# def calculate_sgpa(result):
#     total_credits, total_weighted_grades = 0, 0
#     for row in result:
#         credits_parts = [float(part) for part in row["Credits"].split('+')]
#         grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
#         total_credits += sum(credits_parts)
#         total_weighted_grades += grade * sum(credits_parts)
#     sgpa = total_weighted_grades / total_credits if total_credits else 0
#     return sgpa, total_credits


# def calculate_cgpa(registration, name):
#     rows = list(cutm_collection.find({"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Credits": 1, "Grade": 1}))
#     total_credits, total_weighted_grades = 0, 0
#     for row in rows:
#         credits_parts = [float(part) for part in row["Credits"].split('+')]
#         grade = convert_grade_to_integer(row["Grade"]) if row["Grade"] in "OEABCDSMF" else float(row["Grade"])
#         total_credits += sum(credits_parts)
#         total_weighted_grades += grade * sum(credits_parts)
#     cgpa = total_weighted_grades / total_credits if total_credits else 0
#     return cgpa


# # ---------------- Home ----------------
# @app.route('/', methods=['GET', 'POST'])
# def home():
#     try:
#         if request.method == 'POST' and request.form.get('registration'):
#             registration = request.form.get('registration')
#             semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
#         else:
#             semesters = sorted({doc["Sem"] for doc in cutm_collection.find({}, {"Sem": 1})})

#         result, count, sgpa, total_credits, cgpa, total_all_semester_credits, message = [], 0, None, None, None, 0, None

#         if request.method == 'POST':
#             name = request.form.get('name')
#             registration = request.form.get('registration')
#             semester = request.form.get('semester')

#             result = list(cutm_collection.find(
#                 {"$and": [{"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Sem": semester}]},
#                 {"_id": 0}
#             ))
#             count = len(result)

#             if count == 0:
#                 message = "No records found for the entered name or registration number."

#             if result:
#                 sgpa, total_credits = calculate_sgpa(result)

#             all_credits = cutm_collection.find({"Reg_No": registration}, {"Credits": 1, "_id": 0})
#             total_all_semester_credits = sum(sum(float(part) for part in row["Credits"].split('+')) for row in all_credits)

#             cgpa = calculate_cgpa(registration, name)

#             # Log search
#             user_input_collection.insert_one({
#                 "registration": registration,
#                 "semester": semester,
#                 "time": convert_to_ist(datetime.utcnow())
#             })

#             return render_template('display.html', result=result, count=count, sgpa=sgpa, total_credits=total_credits,
#                                    cgpa=cgpa, total_all_semester_credits=total_all_semester_credits, message=message,
#                                    selected_semester=semester, semesters=semesters)

#         return render_template('index.html', semesters=semesters)
#     except Exception as e:
#         return render_template('index.html', error=str(e))


# # ---------------- Get Semesters ----------------
# @app.route('/semesters', methods=['POST'])
# def get_semesters():
#     try:
#         registration = request.form.get('registration')
#         semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1})})
#         return jsonify(semesters=semesters)
#     except Exception as e:
#         return jsonify(error=str(e))


# # ---------------- Update Data ----------------
# UPLOAD_FOLDER = 'uploads'
# ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# @app.route('/update_data', methods=['GET', 'POST'])
# def update_data():
#     if request.method == 'POST':
#         if 'files' not in request.files:
#             return render_template('update_data.html', error="No file part")
        
#         files = request.files.getlist('files')
#         if not files or all(f.filename == '' for f in files):
#             return render_template('update_data.html', error="No selected files")
        
#         updated_count = 0
#         inserted_count = 0

#         for file in files:
#             if file and allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 # Read file in-memory instead of saving to disk for speed
#                 file_data = file.read()
#                 if filename.endswith('.csv'):
#                     df = pd.read_csv(io.BytesIO(file_data))
#                 else:
#                     df = pd.read_excel(io.BytesIO(file_data))

#                 for _, row in df.iterrows():
#                     # Normalize all keys
#                     reg_no = str(row.get('Reg_No') or row.get('Registration No.') or "").strip().upper()
#                     subject_code = str(row.get('Subject_Code') or row.get('Subject Code') or "").strip().upper()
#                     subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
#                     name = str(row.get('Name') or "").strip()
#                     sem = str(row.get('Sem') or "").strip()
#                     credits = str(row.get('Credits') or row.get('Credit') or "").strip()
#                     grade = str(row.get('Grade') or row.get('Grade Point') or "").strip().upper()
#                     subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()
#                     sem_value = f"Sem {sem}" if sem.isdigit() else sem

#                     if not reg_no or not subject_code:
#                         continue  # skip invalid rows

#                     existing_record = cutm_collection.find_one({
#                         "Reg_No": reg_no,
#                         "Subject_Code": subject_code
#                     })

#                     if existing_record:
#                         # Update only if existing grade in DB is F, S, or M
#                         if existing_record.get("Grade") in {'F', 'S', 'M'}:
#                             cutm_collection.update_one(
#                                 {"Reg_No": reg_no, "Subject_Code": subject_code},
#                                 {"$set": {"Grade": grade}}
#                             )
#                             updated_count += 1
#                             print(f"Updated {reg_no}-{subject_code} from {existing_record.get('Grade')} to {grade}")
#                     else:
#                         # Insert new record with any grade
#                         cutm_collection.insert_one({
#                             "Reg_No": reg_no,
#                             "Subject_Code": subject_code,
#                             "Grade": grade,
#                             "Name": name,
#                             "Sem": sem_value,
#                             "Subject_Name": subject_name,
#                             "Subject_Type": subject_type,
#                             "credits": credits
#                         })
#                         inserted_count += 1
#                         print(f"Inserted new record {reg_no}-{subject_code} with grade {grade}")

#         message = f"All files processed successfully! Updated: {updated_count}, Inserted: {inserted_count}"
#         return render_template('update_data.html', success=message)

#     return render_template('update_data.html')


# # # ---------------- View Data ----------------
# # @app.route('/view_data', methods=['GET', 'POST'])
# # def view_data():
# #     if request.method == 'POST':
# #         reg_no = request.form.get('reg_no')
# #         subject_code = request.form.get('subject_code')
# #         new_grade = request.form.get('new_grade')
# #         if reg_no and subject_code and new_grade:
# #             cutm_collection.update_one({"Reg_No": reg_no, "Subject_Code": subject_code}, {"$set": {"Grade": new_grade}})

# #     rows = list(cutm_collection.find({}, {"_id": 0}))
# #     return render_template('view_data.html', rows=rows)


# # ---------------- Backlog ----------------
# @app.route('/backlog', methods=['GET', 'POST'])
# def backlog():
#     try:
#         result, count, message, search_type = [], 0, None, None
#         if request.method == 'POST':
#             reg_no = request.form.get('registration')
#             subject_name = request.form.get('subject')

#             if reg_no:
#                 search_type = 'registration'
#                 result = list(cutm_collection.find({"Reg_No": reg_no, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
#                 count = len(result)
#                 if count == 0:
#                     message = f"No backlog found for registration number {reg_no}."
#             elif subject_name:
#                 search_type = 'subject'
#                 result = list(cutm_collection.find({"Subject_Name": {"$regex": subject_name, "$options": "i"}, "Grade": {"$in": ["F", "M", "S"]}}, {"_id": 0}))
#                 count = len(result)
#                 if count == 0:
#                     message = f"No students found with backlog in subject '{subject_name}'."
#             else:
#                 message = "Please enter a registration number or subject name to search."

#         return render_template('backlog.html', result=result, count=count, message=message, search_type=search_type)
#     except Exception as e:
#         return render_template('backlog.html', error=str(e))


# # ---------------- Admin ----------------
# @app.route('/admin/login', methods=['GET', 'POST'])
# def admin_login():
#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
#         if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
#             return redirect('/admin/panel')
#         else:
#             return render_template('admin_login.html', error="Invalid username or password")
#     return render_template('admin_login.html')


# @app.route('/about')
# def about():
#     return render_template('about.html')


# @app.route('/admin/panel')
# def admin_panel():
#     return render_template('admin_panel.html')


# # ---------------- Run ----------------
# if __name__ == '__main__':
#     app.run(port=5000, host="0.0.0.0", debug=False)  # debug=False for speed

 




















from flask import Flask, render_template, request, redirect, jsonify
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz
import pandas as pd
from werkzeug.utils import secure_filename
import io  # for in-memory file reading

load_dotenv()

app = Flask(__name__)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI, w=1, retryWrites=True, socketTimeoutMS=20000)
db = client.get_database("cutm")
cutm_collection = db.get_collection("CUTM")

# ---------------- Indexes (biggest speed-up for queries) ----------------
def ensure_indexes():
    try:
        cutm_collection.create_index([("Reg_No", 1)])
        cutm_collection.create_index([("Sem", 1)])
        cutm_collection.create_index([("Reg_No", 1), ("Sem", 1)])
        cutm_collection.create_index([("Name", 1)])
        cutm_collection.create_index([("Subject_Code", 1)])
        # Unique if your data design guarantees one subject_code per student
        # cutm_collection.create_index([("Reg_No", 1), ("Subject_Code", 1)], unique=True)
    except Exception:
        # Make index creation best-effort
        pass

ensure_indexes()

# ---------------- Utilities ----------------
def convert_to_ist(gmt_time):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    gmt_time = gmt_time.replace(tzinfo=pytz.utc)
    return gmt_time.astimezone(ist_timezone).strftime('%Y-%m-%d %I:%M:%S %p IST')

GRADE_MAP = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'S': 0, 'M': 0, 'F': 0}

def convert_grade_to_integer(grade):
    return GRADE_MAP.get(grade, 0)

def calculate_sgpa(result):
    total_credits, total_weighted_grades = 0, 0
    for row in result:
        # Defensive: handle missing or malformed credits
        credits_str = row.get("Credits") or ""
        parts = [p for p in str(credits_str).split('+') if p.strip() != ""]
        if not parts:
            continue
        credits_parts = [float(part) for part in parts]
        # Grade can be letter or numeric string
        g = row.get("Grade")
        grade = convert_grade_to_integer(g) if isinstance(g, str) and g in "OEABCDSMF" else float(g)
        csum = sum(credits_parts)
        total_credits += csum
        total_weighted_grades += grade * csum
    sgpa = total_weighted_grades / total_credits if total_credits else 0
    return sgpa, total_credits

def calculate_cgpa(registration, name):
    # Use projection to minimize data transferred
    cursor = cutm_collection.find(
        {"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]},
        {"Credits": 1, "Grade": 1, "_id": 0}
    )
    total_credits, total_weighted_grades = 0, 0
    for row in cursor:
        credits_str = row.get("Credits") or ""
        parts = [p for p in str(credits_str).split('+') if p.strip() != ""]
        if not parts:
            continue
        credits_parts = [float(part) for part in parts]
        g = row.get("Grade")
        grade = convert_grade_to_integer(g) if isinstance(g, str) and g in "OEABCDSMF" else float(g)
        csum = sum(credits_parts)
        total_credits += csum
        total_weighted_grades += grade * csum
    cgpa = total_weighted_grades / total_credits if total_credits else 0
    return cgpa

# ---------------- Home ----------------
@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        if request.method == 'POST' and request.form.get('registration'):
            registration = (request.form.get('registration') or "").strip().upper()
            semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1, "_id": 0})})
        else:
            semesters = sorted({doc["Sem"] for doc in cutm_collection.find({}, {"Sem": 1, "_id": 0})})

        result, count, sgpa, total_credits, cgpa, total_all_semester_credits, message = [], 0, None, None, None, 0, None

        if request.method == 'POST':
            name = (request.form.get('name') or "").strip()
            registration = (request.form.get('registration') or "").strip().upper()
            semester = (request.form.get('semester') or "").strip()

            if not registration and not name:
                # Avoid full-scan if both empty
                return render_template('index.html', semesters=semesters, error="Please enter registration or name.")

            query = {"$and": [{"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Sem": semester}]}
            projection = {"_id": 0, "Credits": 1, "Grade": 1, "Subject_Name": 1, "Subject_Code": 1, "Sem": 1, "Name": 1, "Reg_No": 1}
            result = list(cutm_collection.find(query, projection))
            count = len(result)

            if count == 0:
                message = "No records found for the entered name or registration number."

            if result:
                sgpa, total_credits = calculate_sgpa(result)

            # Total credits across all semesters for this registration
            total_all_semester_credits = 0
            if registration:
                all_credits = cutm_collection.find({"Reg_No": registration}, {"Credits": 1, "_id": 0})
                for row in all_credits:
                    credits_str = row.get("Credits") or ""
                    parts = [p for p in str(credits_str).split('+') if p.strip() != ""]
                    if not parts:
                        continue
                    total_all_semester_credits += sum(float(part) for part in parts)

            cgpa = calculate_cgpa(registration, name)

            # Removed: logging to user_input_collection

            return render_template(
                'display.html',
                result=result, count=count, sgpa=sgpa, total_credits=total_credits,
                cgpa=cgpa, total_all_semester_credits=total_all_semester_credits, message=message,
                selected_semester=semester, semesters=semesters
            )

        return render_template('index.html', semesters=semesters)
    except Exception as e:
        return render_template('index.html', error=str(e))

# ---------------- Get Semesters ----------------
@app.route('/semesters', methods=['POST'])
def get_semesters():
    try:
        registration = (request.form.get('registration') or "").strip().upper()
        if not registration:
            return jsonify(semesters=[])
        semesters = sorted({doc["Sem"] for doc in cutm_collection.find({"Reg_No": registration}, {"Sem": 1, "_id": 0})})
        return jsonify(semesters=semesters)
    except Exception as e:
        return jsonify(error=str(e))

# ---------------- Update Data ----------------
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/update_data', methods=['GET', 'POST'])
def update_data():
    if request.method == 'POST':
        if 'files' not in request.files:
            return render_template('update_data.html', error="No file part")

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return render_template('update_data.html', error="No selected files")

        updated_count = 0
        inserted_count = 0

        for file in files:
            if not (file and allowed_file(file.filename)):
                continue

            filename = secure_filename(file.filename)
            file_data = file.read()
            if filename.lower().endswith('.csv'):
                # If very large, consider chunksize=5000
                df = pd.read_csv(io.BytesIO(file_data))
            else:
                df = pd.read_excel(io.BytesIO(file_data))

            # Normalize columns once to avoid repeated row.get
            cols = {c.lower().strip(): c for c in df.columns}
            def col(*names):
                for n in names:
                    if n.lower() in cols:
                        return cols[n.lower()]
                return None

            col_reg = col('Reg_No', 'Registration No.')
            col_code = col('Subject_Code', 'Subject Code')
            col_sname = col('Subject_Name', 'Subject Name')
            col_name = col('Name')
            col_sem = col('Sem')
            col_credits = col('Credits', 'Credit')
            col_grade = col('Grade', 'Grade Point')
            col_stype = col('Subject_Type', 'Subject Type')

            for _, row in df.iterrows():
                reg_no = str(row.get(col_reg) or "").strip().upper() if col_reg else ""
                subject_code = str(row.get(col_code) or "").strip().upper() if col_code else ""
                if not reg_no or not subject_code:
                    continue

                subject_name = str(row.get(col_sname) or "").strip() if col_sname else ""
                name = str(row.get(col_name) or "").strip() if col_name else ""
                sem = str(row.get(col_sem) or "").strip() if col_sem else ""
                credits = str(row.get(col_credits) or "").strip() if col_credits else ""
                grade = str(row.get(col_grade) or "").strip().upper() if col_grade else ""
                subject_type = str(row.get(col_stype) or "").strip() if col_stype else ""
                sem_value = f"Sem {sem}" if sem.isdigit() else sem

                existing_record = cutm_collection.find_one(
                    {"Reg_No": reg_no, "Subject_Code": subject_code},
                    {"Grade": 1}
                )

                if existing_record:
                    if existing_record.get("Grade") in {'F', 'S', 'M',''}:
                        cutm_collection.update_one(
                            {"Reg_No": reg_no, "Subject_Code": subject_code},
                            {"$set": {"Grade": grade}}
                        )
                        updated_count += 1
                else:
                    cutm_collection.insert_one({
                        "Reg_No": reg_no,
                        "Subject_Code": subject_code,
                        "Grade": grade,
                        "Name": name,
                        "Sem": sem_value,
                        "Subject_Name": subject_name,
                        "Subject_Type": subject_type,
                        "Credits": credits  # fixed key casing for consistency and speed
                    })
                    inserted_count += 1

        message = f"All files processed successfully! Updated: {updated_count}, Inserted: {inserted_count}"
        return render_template('update_data.html', success=message)

    return render_template('update_data.html')

# ---------------- Backlog ----------------
@app.route('/backlog', methods=['GET', 'POST'])
def backlog():
    try:
        result, count, message, search_type = [], 0, None, None
        if request.method == 'POST':
            reg_no = (request.form.get('registration') or "").strip().upper()
            subject_name = (request.form.get('subject') or "").strip()

            if reg_no:
                search_type = 'registration'
                cursor = cutm_collection.find(
                    {"Reg_No": reg_no, "Grade": {"$in": ["F", "M", "S"]}},
                    {"_id": 0, "Reg_No": 1, "Subject_Code": 1, "Subject_Name": 1, "Grade": 1, "Sem": 1 ,"Name":1}
                )
                result = list(cursor)
                count = len(result)
                if count == 0:
                    message = f"No backlog found for registration number {reg_no}."
            elif subject_name:
                search_type = 'subject'
                cursor = cutm_collection.find(
                    {"Subject_Name": {"$regex": subject_name, "$options": "i"}, "Grade": {"$in": ["F", "M", "S"]}},
                    {"_id": 0, "Reg_No": 1, "Subject_Code": 1, "Subject_Name": 1, "Grade": 1, "Sem": 1, "Name":1}
                )
                result = list(cursor)
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
        username = request.form.get('username') or ""
        password = request.form.get('password') or ""
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
    # For production, prefer a WSGI server:
    # gunicorn app:app -w 4 -k gthread --threads 8 --bind 0.0.0.0:5000
    app.run(port=5000, host="0.0.0.0", debug=False)
