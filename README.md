# 🎓 CUTM Student Result Management System  

A comprehensive web application for managing student academic records, built with **Flask** and **MongoDB**.  
This system provides efficient student data management with features like GPA calculation, backlog tracking, batch-wise filtering, and data export capabilities.

---

## ✨ Features  

### 🔍 Student Records Search
- Search by registration number or student name  
- Semester-wise result filtering  
- Real-time SGPA and CGPA calculation  
- Complete academic history display  

### 📊 GPA Calculation System
- **SGPA**: Semester-wise grade point calculation  
- **CGPA**: Cumulative grade point across all semesters  
- Automatic credit calculation with multi-format support  
- Grade mapping system: *(O=10, E=9, A=8, B=7, C=6, D=5, F=0)*  

### 🎯 Backlog Management
- Track failed subjects (F, M, S, I, R grades)  
- Search by registration number or subject code  
- Branch and year-wise backlog filtering  
- Statistical analysis with visual breakdown  

### 👥 Batch-wise Data Management
- Filter students by academic year (2020–2029)  
- Branch-wise filtering *(Civil, CSE, ECE, EEE, Mechanical)*  
- Complete student records with academic performance  
- Statistical insights and analytics  

### 📁 Data Export Options
- **CSV Export**: Spreadsheet-compatible format  
- **Excel Export**: Professional worksheets with auto-formatted columns  
- **PDF Export**: Formatted reports with institutional branding  

### 🔧 Admin Panel
- Secure admin authentication  
- Bulk data upload *(CSV/Excel)*  
- Individual record updates  
- Data validation and integrity checks  

### 🏗️ Advanced Architecture
- MongoDB indexing for optimized queries  
- Branch identification from registration numbers  
- Year extraction and validation  
- Comprehensive error handling  

---

## 🛠️ Tech Stack  

**Backend**  
- Framework: Flask (Python)  
- Database: MongoDB with PyMongo driver  
- Authentication: Custom admin authentication  
- File Processing: Pandas for CSV/Excel handling  

**Frontend**  
- UI Framework: Bootstrap 5  
- Templates: Jinja2 templating engine  
- Styling: Custom CSS with professional design  
- Responsive: Mobile-friendly interface  

**Data Processing & Export**  
- `pandas` – DataFrame operations  
- `openpyxl` – Excel file generation  
- `reportlab` – PDF document creation  
- File Handling: werkzeug secure filename processing  

**Deployment & Environment**  
- Environment: python-dotenv for configuration  
- Timezone: PyTZ (IST)  
- Security: Environment variable management  

---

## 📋 Prerequisites  

- Python **3.9** or higher  
- MongoDB **4.4** or higher  
- pip (Python package installer)  

---

## 🚀 Installation & Setup  

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/cutm-result-management.git
   cd cutm-result-management
