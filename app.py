from flask import Flask, render_template, request, redirect, json,make_response
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz
import pandas as pd
from werkzeug.utils import secure_filename
import io
from io import StringIO, BytesIO
# from flask import make_response


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
    except Exception:
        pass

ensure_indexes()

#branch identify 
def get_branch_from_reg_no(reg_no):
    """Extract branch name from registration number"""
    branch_codes = {
        '1': 'Civil Engineering',
        '2': 'Computer Science Engineering', 
        '3': 'Electronics & Communication Engineering',
        '5': 'Electrical & Electronics Engineering',
        '6': 'Mechanical Engineering'
    }
    
    if len(str(reg_no)) >= 10:
        branch_code = str(reg_no)[7:8]
        return branch_codes.get(branch_code, 'Unknown Branch')
    return 'Invalid Registration'

def get_year_from_reg_no(reg_no):
    """Extract admission year from registration number"""
    year_codes = {
        '20': '2020',
        '21': '2021', 
        '22': '2022',
        '23': '2023',
        '24': '2024',
        '25': '2025',
        '26': '2026',
        '27': '2027', 
        '28': '2028',
        '29': '2029'
        
    }
    
    if len(str(reg_no)) >= 2:
        year_code = str(reg_no)[:2]
        return year_codes.get(year_code, f'20{year_code}')
    return 'Unknown'

def get_branch_code_mapping():
    """Get branch name to code mapping for search"""
    return {
         'Civil': '1',
         'CSE': '2',
         'ECE': '3',
         'EEE': '5',
         'Mechanical': '6'
    }

def get_year_code_mapping():
    """Get year to code mapping for search"""
    return {
         '20': '2020',
        '21': '2021', 
        '22': '2022',
        '23': '2023',
        '24': '2024',
        '25': '2025',
        '26': '2026',
        '27': '2027', 
        '28': '2028',
        '29': '2029'
    }













# ---------------- Utilities ----------------
def convert_to_ist(gmt_time):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    gmt_time = gmt_time.replace(tzinfo=pytz.utc)
    return gmt_time.astimezone(ist_timezone).strftime('%Y-%m-%d %I:%M:%S %p IST')

GRADE_MAP = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'S': 0, 'M': 0, 'F': 0, "I" :0,"R":0}

def convert_grade_to_integer(grade):
    return GRADE_MAP.get(grade, 0)

def calculate_sgpa(result):
    total_credits, total_weighted_grades = 0, 0
    for row in result:
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
    sgpa = total_weighted_grades / total_credits if total_credits else 0
    return sgpa, total_credits

def calculate_cgpa(registration, name):
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
                return render_template('index.html', semesters=semesters, error="Please enter registration or name.")

            query = {"$and": [{"$or": [{"Reg_No": registration}, {"Name": {"$regex": f"^{name}$", "$options": "i"}}]}, {"Sem": semester}]}
            projection = {"_id": 0, "Credits": 1, "Grade": 1, "Subject_Name": 1, "Subject_Code": 1, "Sem": 1, "Name": 1, "Reg_No": 1}
            result = list(cutm_collection.find(query, projection))
            count = len(result)

            if count == 0:
                message = "No records found for the entered name or registration number."

            if result:
                sgpa, total_credits = calculate_sgpa(result)

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
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}

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
                df = pd.read_csv(io.BytesIO(file_data))
            else:
                df = pd.read_excel(io.BytesIO(file_data))

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
                    if existing_record.get("Grade") in {'F', 'S', 'M','I','R',''}:
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
                        "Credits": credits
                    })
                    inserted_count += 1

        message = f"All files processed successfully! Updated: {updated_count}, Inserted: {inserted_count}"
        return render_template('update_data.html', success=message)

    return render_template('update_data.html')

# ---------------- Backlog ----------------
 

# @app.route('/backlog', methods=['GET', 'POST'])
# def backlog():
#     try:
#         result, count, message, search_type = [], 0, None, None
#         branch_stats = {}
#         year_stats = {}
#         search_criteria = []
        
#         if request.method == 'POST':
#             reg_no = (request.form.get('registration') or "").strip().upper()
#             subject_code = (request.form.get('subject_code') or "").strip().upper()
#             branch_filter = (request.form.get('branch') or "").strip()
#             year_filter = (request.form.get('year') or "").strip()

#             base_query = {"Grade": {"$in": ["F", "M", "S", "I", "R"]}}
#             reg_conditions = []  # Store regex conditions for Reg_No field
            
#             # Build search criteria based on provided filters
#             if reg_no:
#                 search_type = 'registration'
#                 base_query["Reg_No"] = reg_no
#                 search_criteria.append(f"Registration: {reg_no}")
                
#             elif subject_code:
#                 search_type = 'subject_code'
#                 base_query["Subject_Code"] = subject_code
#                 search_criteria.append(f"Subject Code: {subject_code}")
                
#                 # Add branch filter if provided with subject code
#                 if branch_filter:
#                     branch_codes = get_branch_code_mapping()
#                     branch_code = None
                    
#                     for branch_name, code in branch_codes.items():
#                         if branch_filter.lower() in branch_name.lower():
#                             branch_code = code
#                             break
                    
#                     if branch_code:
#                         search_criteria.append(f"Branch: {branch_filter}")
#                         reg_conditions.append({"Reg_No": {"$regex": f".{{7}}{branch_code}"}})
#                     else:
#                         message = f"Invalid branch selection: {branch_filter}"
                
#                 # Add year filter if provided with subject code
#                 if year_filter and not message:
#                     year_codes = get_year_code_mapping()
#                     year_code = None
#                     year_short = year_filter
                    
#                     # Handle both 2-digit and 4-digit year inputs
#                     if year_filter in year_codes:
#                         year_code = year_codes[year_filter]
#                     elif len(year_filter) == 4 and year_filter.isdigit():
#                         year_short = year_filter[-2:]  # Get last 2 digits
#                         if year_short in year_codes:
#                             year_code = year_codes[year_short]
                    
#                     if year_code:
#                         search_criteria.append(f"Year: {year_filter}")
#                         reg_conditions.append({"Reg_No": {"$regex": f"^{year_short}"}})
#                     else:
#                         message = f"Invalid year selection: {year_filter}"
                
#                 # Apply multiple regex conditions using $and
#                 if reg_conditions and not message:
#                     if len(reg_conditions) == 1:
#                         base_query.update(reg_conditions[0])
#                     else:
#                         base_query["$and"] = reg_conditions
                        
#             elif branch_filter or year_filter:
#                 search_type = 'advanced'
                
#                 # Branch filtering
#                 if branch_filter:
#                     branch_codes = get_branch_code_mapping()
#                     branch_code = None
                    
#                     for branch_name, code in branch_codes.items():
#                         if branch_filter.lower() in branch_name.lower():
#                             branch_code = code
#                             break
                    
#                     if branch_code:
#                         search_criteria.append(f"Branch: {branch_filter}")
#                         reg_conditions.append({"Reg_No": {"$regex": f".{{7}}{branch_code}"}})
#                     else:
#                         message = f"Invalid branch selection: {branch_filter}"
                
#                 # Year filtering  
#                 if year_filter and not message:
#                     year_codes = get_year_code_mapping()
#                     year_code = None
#                     year_short = year_filter
                    
#                     # Handle both 2-digit and 4-digit year inputs
#                     if year_filter in year_codes:
#                         year_code = year_codes[year_filter]
#                     elif len(year_filter) == 4 and year_filter.isdigit():
#                         year_short = year_filter[-2:]  # Get last 2 digits
#                         if year_short in year_codes:
#                             year_code = year_codes[year_short]
                    
#                     if year_code:
#                         search_criteria.append(f"Year: {year_filter}")
#                         reg_conditions.append({"Reg_No": {"$regex": f"^{year_short}"}})
#                     else:
#                         message = f"Invalid year selection: {year_filter}"
                
#                 # Apply multiple regex conditions using $and
#                 if reg_conditions and not message:
#                     if len(reg_conditions) == 1:
#                         base_query.update(reg_conditions[0])
#                     else:
#                         base_query["$and"] = reg_conditions

#             if not message and (reg_no or subject_code or branch_filter or year_filter):
#                 cursor = cutm_collection.find(
#                     base_query,
#                     {"_id": 0, "Reg_No": 1, "Subject_Code": 1, "Subject_Name": 1, 
#                      "Grade": 1, "Sem": 1, "Name": 1}
#                 )
#                 result = list(cursor)
#                 count = len(result)
                
#                 # Add branch and year information to results
#                 for row in result:
#                     row['Branch'] = get_branch_from_reg_no(row.get('Reg_No', ''))
#                     row['Year'] = get_year_from_reg_no(row.get('Reg_No', ''))
#                     # Create short branch name for display
#                     if row['Branch'] != 'Unknown Branch':
#                         row['Branch_Short'] = row['Branch'].split()[0]
#                     else:
#                         row['Branch_Short'] = 'Unknown'
                
#                 # Calculate statistics
#                 for row in result:
#                     branch = row.get('Branch_Short', 'Unknown')
#                     year = row.get('Year', 'Unknown')
#                     branch_stats[branch] = branch_stats.get(branch, 0) + 1
#                     year_stats[year] = year_stats.get(year, 0) + 1
                
#                 if count == 0:
#                     if search_type == 'registration':
#                         message = f"No backlog found for registration number {reg_no}."
#                     elif search_type == 'subject_code':
#                         criteria_text = ", ".join(search_criteria)
#                         message = f"No students found with backlog for: {criteria_text}."
#                     elif search_type == 'advanced':
#                         criteria_text = ", ".join(search_criteria)
#                         message = f"No backlog found for criteria: {criteria_text}."
#             elif not (reg_no or subject_code or branch_filter or year_filter):
#                 message = "Please enter a registration number, subject code, or select branch/year to search."

#         return render_template('backlog.html', 
#                              result=result, 
#                              count=count, 
#                              message=message, 
#                              search_type=search_type,
#                              branch_stats=branch_stats,
#                              year_stats=year_stats,
#                              search_criteria=search_criteria)
#     except Exception as e:
#         return render_template('backlog.html', error=str(e))
@app.route('/backlog', methods=['GET', 'POST'])
def backlog():
    try:
        result, count, message, search_type = [], 0, None, None
        branch_stats = {}
        year_stats = {}
        search_criteria = []
        
        if request.method == 'POST':
            reg_no = (request.form.get('registration') or "").strip().upper()
            subject_code = (request.form.get('subject_code') or "").strip().upper()
            branch_filter = (request.form.get('branch') or "").strip()
            year_filter = (request.form.get('year') or "").strip()

            base_query = {"Grade": {"$in": ["F", "M", "S", "I", "R"]}}
            reg_conditions = []
            
            # Helper function to get branch code from user input
            def get_branch_code_from_input(branch_input):
                """Get branch code from various input formats"""
                branch_mapping = {
                    'civil': '1',
                    'civil engineering': '1',
                    'cse': '2', 
                    'computer science': '2',
                    'computer science engineering': '2',
                    'ece': '3',
                    'electronics': '3',
                    'electronics & communication': '3',
                    'electronics & communication engineering': '3',
                    'eee': '5',
                    'electrical': '5',
                    'electrical & electronics': '5',
                    'electrical & electronics engineering': '5',
                    'mechanical': '6',
                    'mechanical engineering': '6'
                }
                
                branch_lower = branch_input.lower().strip()
                return branch_mapping.get(branch_lower)
            
            if reg_no:
                search_type = 'registration'
                base_query["Reg_No"] = reg_no
                search_criteria.append(f"Registration: {reg_no}")
                
            elif subject_code:
                search_type = 'subject_code'
                base_query["Subject_Code"] = subject_code
                search_criteria.append(f"Subject Code: {subject_code}")
                
                # Add branch filter if provided with subject code
                if branch_filter:
                    branch_code = get_branch_code_from_input(branch_filter)
                    
                    if branch_code:
                        search_criteria.append(f"Branch: {branch_filter}")
                        # Fixed regex: match any 7 characters, then the branch code at position 7
                        reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
                    else:
                        message = f"Invalid branch selection: {branch_filter}. Valid options: Civil, CSE, ECE, EEE, Mechanical"
                
                # Add year filter if provided with subject code
                if year_filter and not message:
                    year_short = year_filter
                    
                    # Handle both 2-digit and 4-digit year inputs
                    if len(year_filter) == 4 and year_filter.isdigit():
                        year_short = year_filter[-2:]  # Get last 2 digits
                    elif len(year_filter) == 2 and year_filter.isdigit():
                        year_short = year_filter
                    else:
                        message = f"Invalid year format: {year_filter}. Use format: 21, 22, 2021, 2022, etc."
                    
                    if not message:
                        search_criteria.append(f"Year: {year_filter}")
                        # Fixed regex: match year at the beginning
                        reg_conditions.append({"Reg_No": {"$regex": f"^{year_short}"}})
                
                # Apply regex conditions properly
                if reg_conditions and not message:
                    if len(reg_conditions) == 1:
                        base_query.update(reg_conditions[0])
                    else:
                        # Use $and to combine multiple regex conditions
                        base_query["$and"] = reg_conditions
                        
            elif branch_filter or year_filter:
                search_type = 'advanced'
                
                # Branch filtering for advanced search
                if branch_filter:
                    branch_code = get_branch_code_from_input(branch_filter)
                    
                    if branch_code:
                        search_criteria.append(f"Branch: {branch_filter}")
                        reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
                    else:
                        message = f"Invalid branch selection: {branch_filter}. Valid options: Civil, CSE, ECE, EEE, Mechanical"
                
                # Year filtering for advanced search
                if year_filter and not message:
                    year_short = year_filter
                    
                    if len(year_filter) == 4 and year_filter.isdigit():
                        year_short = year_filter[-2:]
                    elif len(year_filter) == 2 and year_filter.isdigit():
                        year_short = year_filter
                    else:
                        message = f"Invalid year format: {year_filter}. Use format: 21, 22, 2021, 2022, etc."
                    
                    if not message:
                        search_criteria.append(f"Year: {year_filter}")
                        reg_conditions.append({"Reg_No": {"$regex": f"^{year_short}"}})
                
                # Apply regex conditions for advanced search
                if reg_conditions and not message:
                    if len(reg_conditions) == 1:
                        base_query.update(reg_conditions[0])
                    else:
                        base_query["$and"] = reg_conditions

            # Execute query if no errors
            if not message and (reg_no or subject_code or branch_filter or year_filter):
                cursor = cutm_collection.find(
                    base_query,
                    {"_id": 0, "Reg_No": 1, "Subject_Code": 1, "Subject_Name": 1, 
                     "Grade": 1, "Sem": 1, "Name": 1}
                )
                result = list(cursor)
                count = len(result)
                
                # Add branch and year information to results
                for row in result:
                    row['Branch'] = get_branch_from_reg_no(row.get('Reg_No', ''))
                    row['Year'] = get_year_from_reg_no(row.get('Reg_No', ''))
                    if row['Branch'] != 'Unknown Branch':
                        row['Branch_Short'] = row['Branch'].split()[0]
                    else:
                        row['Branch_Short'] = 'Unknown'
                
                # Calculate statistics
                for row in result:
                    branch = row.get('Branch_Short', 'Unknown')
                    year = row.get('Year', 'Unknown')
                    branch_stats[branch] = branch_stats.get(branch, 0) + 1
                    year_stats[year] = year_stats.get(year, 0) + 1
                
                if count == 0:
                    if search_type == 'registration':
                        message = f"No backlog found for registration number {reg_no}."
                    elif search_type == 'subject_code':
                        criteria_text = ", ".join(search_criteria)
                        message = f"No students found with backlog for: {criteria_text}."
                    elif search_type == 'advanced':
                        criteria_text = ", ".join(search_criteria)
                        message = f"No backlog found for criteria: {criteria_text}."
            elif not (reg_no or subject_code or branch_filter or year_filter):
                message = "Please enter a registration number, subject code, or select branch/year to search."

        return render_template('backlog.html', 
                             result=result, 
                             count=count, 
                             message=message, 
                             search_type=search_type,
                             branch_stats=branch_stats,
                             year_stats=year_stats,
                             search_criteria=search_criteria)
    except Exception as e:
        return render_template('backlog.html', error=str(e))









# ---------------- Batch Route ----------------
@app.route('/batch', methods=['GET', 'POST'])
def batch():
    try:
        result, count, message = [], 0, None
        branch_stats = {}
        batch_stats = {}
        search_criteria = []
        
        if request.method == 'POST':
            branch_filter = (request.form.get('branch') or "").strip()
            batch_filter = (request.form.get('batch') or "").strip()
            
            base_query = {}
            reg_conditions = []
            
            # Helper function to get branch code from user input
            def get_branch_code_from_input(branch_input):
                """Get branch code from various input formats"""
                branch_mapping = {
                    'civil': '1',
                    'civil engineering': '1',
                    'cse': '2', 
                    'computer science': '2',
                    'computer science engineering': '2',
                    'ece': '3',
                    'electronics': '3',
                    'electronics & communication': '3',
                    'electronics & communication engineering': '3',
                    'eee': '5',
                    'electrical': '5',
                    'electrical & electronics': '5',
                    'electrical & electronics engineering': '5',
                    'mechanical': '6',
                    'mechanical engineering': '6'
                }
                
                branch_lower = branch_input.lower().strip()
                return branch_mapping.get(branch_lower)
            
            # Branch filtering
            if branch_filter:
                branch_code = get_branch_code_from_input(branch_filter)
                
                if branch_code:
                    search_criteria.append(f"Branch: {branch_filter}")
                    # Match any 7 characters, then the branch code at position 7
                    reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
                else:
                    message = f"Invalid branch selection: {branch_filter}. Valid options: Civil, CSE, ECE, EEE, Mechanical"
            
            # Batch/Year filtering
            if batch_filter and not message:
                batch_short = batch_filter
                
                # Handle both 2-digit and 4-digit year inputs
                if len(batch_filter) == 4 and batch_filter.isdigit():
                    batch_short = batch_filter[-2:]  # Get last 2 digits
                elif len(batch_filter) == 2 and batch_filter.isdigit():
                    batch_short = batch_filter
                else:
                    message = f"Invalid batch format: {batch_filter}. Use format: 21, 22, 2021, 2022, etc."
                
                if not message:
                    search_criteria.append(f"Batch: {batch_filter}")
                    # Match batch year at the beginning
                    reg_conditions.append({"Reg_No": {"$regex": f"^{batch_short}"}})
            
            # Apply regex conditions
            if reg_conditions and not message:
                if len(reg_conditions) == 1:
                    base_query.update(reg_conditions[0])
                else:
                    # Use $and to combine multiple regex conditions
                    base_query["$and"] = reg_conditions
            
            # Execute query if conditions are provided
            if not message and (branch_filter or batch_filter):
                # Get unique students first, then get all their records
                if base_query:
                    # Get all records matching the criteria
                    cursor = cutm_collection.find(
                        base_query,
                        {"_id": 0, "Reg_No": 1, "Name": 1, "Sem": 1, 
                         "Subject_Code": 1, "Subject_Name": 1, "Credits": 1, "Grade": 1}
                    ).sort([("Reg_No", 1), ("Sem", 1), ("Subject_Code", 1)])
                    
                    result = list(cursor)
                    count = len(result)
                    
                    # Add branch and batch information to results
                    unique_students = set()
                    for row in result:
                        reg_no = row.get('Reg_No', '')
                        row['Branch'] = get_branch_from_reg_no(reg_no)
                        row['Batch'] = get_year_from_reg_no(reg_no)
                        
                        if row['Branch'] != 'Unknown Branch':
                            row['Branch_Short'] = row['Branch'].split()[0]
                        else:
                            row['Branch_Short'] = 'Unknown'
                        
                        unique_students.add(reg_no)
                    
                    # Calculate statistics
                    for row in result:
                        branch = row.get('Branch_Short', 'Unknown')
                        batch = row.get('Batch', 'Unknown')
                        branch_stats[branch] = branch_stats.get(branch, 0) + 1
                        batch_stats[batch] = batch_stats.get(batch, 0) + 1
                    
                    # Update count to show unique students count
                    student_count = len(unique_students)
                    
                    if count == 0:
                        criteria_text = ", ".join(search_criteria)
                        message = f"No records found for criteria: {criteria_text}."
                    else:
                        success_criteria = ", ".join(search_criteria)
                        message = f"Found {count} records for {student_count} students matching: {success_criteria}."
                else:
                    message = "Please select at least one filter (branch or batch)."
            elif not message:
                message = "Please select branch and/or batch to view data."
        
        return render_template('batch.html', 
                             result=result, 
                             count=count, 
                             message=message,
                             branch_stats=branch_stats,
                             batch_stats=batch_stats,
                             search_criteria=search_criteria)
                             
    except Exception as e:
        return render_template('batch.html', error=str(e))








 

# ---------------- Export Routes for Batch Data ----------------
@app.route('/export_batch_csv', methods=['POST'])
def export_batch_csv():
    try:
        # Get the same query parameters from the form
        branch_filter = (request.form.get('branch') or "").strip()
        batch_filter = (request.form.get('batch') or "").strip()
        
        # Recreate the same query logic as in batch route
        base_query = {}
        reg_conditions = []
        
        def get_branch_code_from_input(branch_input):
            branch_mapping = {
                'civil': '1', 'civil engineering': '1',
                'cse': '2', 'computer science': '2', 'computer science engineering': '2',
                'ece': '3', 'electronics': '3', 'electronics & communication': '3', 'electronics & communication engineering': '3',
                'eee': '5', 'electrical': '5', 'electrical & electronics': '5', 'electrical & electronics engineering': '5',
                'mechanical': '6', 'mechanical engineering': '6'
            }
            return branch_mapping.get(branch_input.lower().strip())
        
        if branch_filter:
            branch_code = get_branch_code_from_input(branch_filter)
            if branch_code:
                reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
        
        if batch_filter:
            batch_short = batch_filter
            if len(batch_filter) == 4 and batch_filter.isdigit():
                batch_short = batch_filter[-2:]
            reg_conditions.append({"Reg_No": {"$regex": f"^{batch_short}"}})
        
        if reg_conditions:
            if len(reg_conditions) == 1:
                base_query.update(reg_conditions[0])
            else:
                base_query["$and"] = reg_conditions
        
        # Get data
        cursor = cutm_collection.find(
            base_query,
            {"_id": 0, "Reg_No": 1, "Name": 1, "Sem": 1, 
             "Subject_Code": 1, "Subject_Name": 1, "Credits": 1, "Grade": 1}
        ).sort([("Reg_No", 1), ("Sem", 1), ("Subject_Code", 1)])
        
        result = list(cursor)
        
        # Add branch and batch info
        for row in result:
            row['Branch'] = get_branch_from_reg_no(row.get('Reg_No', ''))
            row['Batch'] = get_year_from_reg_no(row.get('Reg_No', ''))
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Registration No', 'Name', 'Branch', 'Batch', 'Semester', 
                        'Subject Code', 'Subject Name', 'Credits', 'Grade'])
        
        # Write data
        for row in result:
            writer.writerow([
                row.get('Reg_No', ''),
                row.get('Name', ''),
                row.get('Branch', ''),
                row.get('Batch', ''),
                row.get('Sem', ''),
                row.get('Subject_Code', ''),
                row.get('Subject_Name', ''),
                row.get('Credits', ''),
                row.get('Grade', '')
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=batch_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        return render_template('batch.html', error=f"Export failed: {str(e)}")

@app.route('/export_batch_excel', methods=['POST'])
def export_batch_excel():
    try:
        # Get the same query parameters from the form
        branch_filter = (request.form.get('branch') or "").strip()
        batch_filter = (request.form.get('batch') or "").strip()
        
        # Recreate the same query logic
        base_query = {}
        reg_conditions = []
        
        def get_branch_code_from_input(branch_input):
            branch_mapping = {
                'civil': '1', 'civil engineering': '1',
                'cse': '2', 'computer science': '2', 'computer science engineering': '2',
                'ece': '3', 'electronics': '3', 'electronics & communication': '3', 'electronics & communication engineering': '3',
                'eee': '5', 'electrical': '5', 'electrical & electronics': '5', 'electrical & electronics engineering': '5',
                'mechanical': '6', 'mechanical engineering': '6'
            }
            return branch_mapping.get(branch_input.lower().strip())
        
        if branch_filter:
            branch_code = get_branch_code_from_input(branch_filter)
            if branch_code:
                reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
        
        if batch_filter:
            batch_short = batch_filter
            if len(batch_filter) == 4 and batch_filter.isdigit():
                batch_short = batch_filter[-2:]
            reg_conditions.append({"Reg_No": {"$regex": f"^{batch_short}"}})
        
        if reg_conditions:
            if len(reg_conditions) == 1:
                base_query.update(reg_conditions[0])
            else:
                base_query["$and"] = reg_conditions
        
        # Get data
        cursor = cutm_collection.find(
            base_query,
            {"_id": 0, "Reg_No": 1, "Name": 1, "Sem": 1, 
             "Subject_Code": 1, "Subject_Name": 1, "Credits": 1, "Grade": 1}
        ).sort([("Reg_No", 1), ("Sem", 1), ("Subject_Code", 1)])
        
        result = list(cursor)
        
        # Add branch and batch info
        for row in result:
            row['Branch'] = get_branch_from_reg_no(row.get('Reg_No', ''))
            row['Batch'] = get_year_from_reg_no(row.get('Reg_No', ''))
        
        # Create DataFrame
        df_data = []
        for row in result:
            df_data.append({
                'Registration No': row.get('Reg_No', ''),
                'Name': row.get('Name', ''),
                'Branch': row.get('Branch', ''),
                'Batch': row.get('Batch', ''),
                'Semester': row.get('Sem', ''),
                'Subject Code': row.get('Subject_Code', ''),
                'Subject Name': row.get('Subject_Name', ''),
                'Credits': row.get('Credits', ''),
                'Grade': row.get('Grade', '')
            })
        
        df = pd.DataFrame(df_data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Batch Data')
            
            # Get the workbook and worksheet
            worksheet = writer.sheets['Batch Data']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=batch_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return response
        
    except Exception as e:
        return render_template('batch.html', error=f"Export failed: {str(e)}")

@app.route('/export_batch_pdf', methods=['POST'])
def export_batch_pdf():
    try:
        # Get the same query parameters from the form
        branch_filter = (request.form.get('branch') or "").strip()
        batch_filter = (request.form.get('batch') or "").strip()
        
        # Recreate the same query logic
        base_query = {}
        reg_conditions = []
        
        def get_branch_code_from_input(branch_input):
            branch_mapping = {
                'civil': '1', 'civil engineering': '1',
                'cse': '2', 'computer science': '2', 'computer science engineering': '2',
                'ece': '3', 'electronics': '3', 'electronics & communication': '3', 'electronics & communication engineering': '3',
                'eee': '5', 'electrical': '5', 'electrical & electronics': '5', 'electrical & electronics engineering': '5',
                'mechanical': '6', 'mechanical engineering': '6'
            }
            return branch_mapping.get(branch_input.lower().strip())
        
        if branch_filter:
            branch_code = get_branch_code_from_input(branch_filter)
            if branch_code:
                reg_conditions.append({"Reg_No": {"$regex": f"^.{{{7}}}{branch_code}"}})
        
        if batch_filter:
            batch_short = batch_filter
            if len(batch_filter) == 4 and batch_filter.isdigit():
                batch_short = batch_filter[-2:]
            reg_conditions.append({"Reg_No": {"$regex": f"^{batch_short}"}})
        
        if reg_conditions:
            if len(reg_conditions) == 1:
                base_query.update(reg_conditions[0])
            else:
                base_query["$and"] = reg_conditions
        
        # Get data
        cursor = cutm_collection.find(
            base_query,
            {"_id": 0, "Reg_No": 1, "Name": 1, "Sem": 1, 
             "Subject_Code": 1, "Subject_Name": 1, "Credits": 1, "Grade": 1}
        ).sort([("Reg_No", 1), ("Sem", 1), ("Subject_Code", 1)])
        
        result = list(cursor)
        
        # Add branch and batch info
        for row in result:
            row['Branch'] = get_branch_from_reg_no(row.get('Reg_No', ''))
            row['Batch'] = get_year_from_reg_no(row.get('Reg_No', ''))
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Add title
        title = Paragraph("Batch Data Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Add filters info
        filter_info = []
        if branch_filter:
            filter_info.append(f"Branch: {branch_filter}")
        if batch_filter:
            filter_info.append(f"Batch: {batch_filter}")
        
        if filter_info:
            filter_text = Paragraph(f"Filters Applied: {', '.join(filter_info)}", styles['Normal'])
            elements.append(filter_text)
            elements.append(Spacer(1, 12))
        
        # Add generation date
        date_text = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        elements.append(date_text)
        elements.append(Spacer(1, 20))
        
        # Create table data
        data = [['Reg No', 'Name', 'Branch', 'Batch', 'Semester', 'Subject Code', 'Subject Name', 'Credits', 'Grade']]
        
        for row in result:
            data.append([
                row.get('Reg_No', ''),
                row.get('Name', ''),
                row.get('Branch', '').split()[0] if row.get('Branch') != 'Unknown Branch' else 'Unknown',
                row.get('Batch', ''),
                row.get('Sem', ''),
                row.get('Subject_Code', ''),
                row.get('Subject_Name', '')[:30] + '...' if len(row.get('Subject_Name', '')) > 30 else row.get('Subject_Name', ''),
                row.get('Credits', ''),
                row.get('Grade', '')
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Create response
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=batch_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        
        return response
        
    except Exception as e:
        return render_template('batch.html', error=f"Export failed: {str(e)}")



















# # ---------------- Admin ----------------
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




# ---------------- View Data with Search & Update ----------------
@app.route('/view_data', methods=['GET', 'POST'])
def view_data():
    try:
        rows = []
        registration = ""
        message = ""
        error = ""
        total_credits = 0
        
        if request.method == 'POST':
            # Check if it's a search request or update request
            if 'search_registration' in request.form:
                # Search functionality
                registration = (request.form.get('search_registration') or "").strip().upper()
                
                if not registration:
                    error = "Please enter a registration number."
                else:
                    # Get all records for this student
                    cursor = cutm_collection.find(
                        {"Reg_No": registration},
                        {"Reg_No": 1, "Name": 1, "Sem": 1, "Subject_Code": 1, 
                         "Subject_Name": 1, "Credits": 1, "Grade": 1, "_id": 0}
                    ).sort([("Sem", 1), ("Subject_Code", 1)])
                    
                    student_data = list(cursor)
                    
                    if not student_data:
                        error = f"No records found for registration number: {registration}"
                    else:
                        # Convert to format expected by template (list of tuples)
                        rows = [(record.get('Reg_No', ''), 
                                record.get('Name', ''),
                                record.get('Sem', ''),
                                record.get('Subject_Code', ''),
                                record.get('Subject_Name', ''),
                                record.get('Credits', ''),
                                record.get('Grade', '')) for record in student_data]
                        
                        # Calculate total credits
                        for record in student_data:
                            credits_str = record.get("Credits") or ""
                            parts = [p for p in str(credits_str).split('+') if p.strip() != ""]
                            if parts:
                                try:
                                    total_credits += sum(float(part) for part in parts)
                                except ValueError:
                                    continue
                        
            elif 'reg_no' in request.form and 'subject_code' in request.form:
                # Update grade functionality
                reg_no = (request.form.get('reg_no') or "").strip().upper()
                subject_code = (request.form.get('subject_code') or "").strip().upper()
                new_grade = (request.form.get('new_grade') or "").strip().upper()
                
                if not all([reg_no, subject_code, new_grade]):
                    error = "All fields are required for update."
                elif new_grade not in ['O', 'E', 'A', 'B', 'C', 'D', 'F', 'M', 'S', 'I', 'R']:
                    error = "Invalid grade. Please use: O, E, A, B, C, D, F, M, S, I, R"
                else:
                    # Update the grade
                    result = cutm_collection.update_one(
                        {"Reg_No": reg_no, "Subject_Code": subject_code},
                        {"$set": {"Grade": new_grade}}
                    )
                    
                    if result.modified_count > 0:
                        message = f"Grade updated successfully for {subject_code}!"
                        # Keep the current registration for search continuity
                        registration = reg_no
                        
                        # Reload the data to show updated grades
                        cursor = cutm_collection.find(
                            {"Reg_No": registration},
                            {"Reg_No": 1, "Name": 1, "Sem": 1, "Subject_Code": 1, 
                             "Subject_Name": 1, "Credits": 1, "Grade": 1, "_id": 0}
                        ).sort([("Sem", 1), ("Subject_Code", 1)])
                        
                        student_data = list(cursor)
                        rows = [(record.get('Reg_No', ''), 
                                record.get('Name', ''),
                                record.get('Sem', ''),
                                record.get('Subject_Code', ''),
                                record.get('Subject_Name', ''),
                                record.get('Credits', ''),
                                record.get('Grade', '')) for record in student_data]
                        
                        # Recalculate total credits after update
                        for record in student_data:
                            credits_str = record.get("Credits") or ""
                            parts = [p for p in str(credits_str).split('+') if p.strip() != ""]
                            if parts:
                                try:
                                    total_credits += sum(float(part) for part in parts)
                                except ValueError:
                                    continue
                    else:
                        error = "No record found to update or grade was already the same."
        
        return render_template('view_data.html', 
                             rows=rows, 
                             registration=registration,
                             message=message,
                             error=error,
                             total_credits=total_credits)
                             
    except Exception as e:
        return render_template('view_data.html', error=str(e))


# Export the app for Vercel
# app = app


#when i host it will commenyt this
if __name__ == "__main__":
    app.run(debug=True)
