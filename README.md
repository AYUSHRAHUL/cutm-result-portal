# 🎓 CUTM Student Result Management System  

A comprehensive web application for managing **student academic records**, built with **Flask** and **MongoDB**.  
This system provides efficient student data management with features like GPA calculation, backlog tracking, batch-wise filtering, and data export capabilities.  

---

## ✨ Features  

- 🔍 **Student Records Search**: Search by registration number or student name, filter by semester, and view real-time SGPA/CGPA calculations.  
- 📊 **GPA Calculation System**: Automatically calculates SGPA (Semester GPA) and CGPA (Cumulative GPA) based on a defined grade mapping system.  
- 🎯 **Backlog Management**: Track failed subjects (grades **F, M, S, I, R**) with filtering by branch and year, and view statistics.  
- 👥 **Batch-wise Data Management**: Filter student records by academic year and branch for performance insights.  
- 📁 **Data Export Options**: Export reports in **CSV, Excel, and PDF** formats with professional formatting and branding.  
- 🔧 **Admin Panel**: Secure interface for bulk uploads, record updates, and data validation.  

---

## 🛠️ Tech Stack  

- **Backend:** Flask, MongoDB (PyMongo), Pandas, PyTZ, python-dotenv  
- **Frontend:** Bootstrap 5, Jinja2, Custom CSS  
- **Data Processing:** Pandas, openpyxl, reportlab, werkzeug  

---

## 📋 Prerequisites  

- 🐍 Python **3.9+**  
- 🍃 MongoDB **4.4+**  
- 📦 pip (Python package installer)  

---

## 🚀 Installation & Setup  

```bash
# Clone the repository
git clone https://github.com/AYUSHRAHUL/cutm-result-management.git
cd cutm-result-management

# Create Virtual Environment
python -m venv venv

# Activate it
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

---

Plaintext

MONGO_URI=mongodb://localhost:27017/your-database
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
Run the Application

Bash

python app.py
Visit http://localhost:5000 to access the application.
 
🎯 Usage Guide
For Students: Check results, view SGPA/CGPA, and track academic progress.

For Faculty: Analyze backlogs, generate batch reports, and export data for analysis.

For Administrators: Upload bulk data, update records, and manage system integrity.

📁 Project Structure
Plaintext

cutm-result-management/
├── app.py                 # Main Flask application
├── templates/            # HTML templates
│   ├── index.html
│   ├── display.html
│   ├── backlog.html
│   ├── batch.html
│   └── admin_login.html
├── static/               # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables
└── README.md            # Project documentation
🤝 Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.

Create a feature branch (git checkout -b feature/amazing-feature).

Commit your changes (git commit -m 'Add amazing feature').

Push to the branch (git push origin feature/amazing-feature).

Open a Pull Request.

📝 License
This project is licensed under the MIT License.

🙏 Acknowledgments
CUTM for the educational data structure inspiration

Flask Community for the robust web framework

MongoDB for flexible document storage

Bootstrap for responsive UI components

Made with ❤️ for educational institutions. Empowering academic management through technology.
