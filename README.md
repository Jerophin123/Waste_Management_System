
# 🗑️ Waste Management System 🚀  


## 🌱 About the Project  
The **Waste Management System** is an AI-powered waste classification and tracking solution that helps in segregating waste into **bio-degradable** and **non-bio-degradable** categories using deep learning. The system processes images and videos to classify waste, visualize data trends, and generate reports for sustainable waste disposal.  

## 🎯 Features  
✅ **Real-time Waste Classification** – Predict waste type using an AI model  
✅ **Video-based Waste Analysis** – Process videos and classify frames  
✅ **Interactive Dashboard** – View statistics with charts and reports  
✅ **PDF & CSV Reports** – Download waste reports in multiple formats  
✅ **Email Notifications** – Send waste reports via email  
✅ **RESTful API** – Easily integrate waste classification into other systems  

## 🏗️ Tech Stack  
🔹 **Frontend:** React.js, Material-UI, Chart.js, Framer Motion  
🔹 **Backend:** Flask, TensorFlow, Keras, OpenCV  
🔹 **Database:** SQLite  
🔹 **Visualization:** ReportLab, Matplotlib  
🔹 **Email Notifications:** SMTP, Python Email API  

## ⚠️ Python Version Requirement  
🟢 **This project runs only on Python 3.9.**  
Ensure that you have Python **3.9.x** installed before proceeding.  

Check your Python version:
```sh
python --version
```
If you don’t have Python 3.9 installed, download it from: [Python 3.9 Downloads](https://www.python.org/downloads/release/python-390/)


## 🚀 Getting Started  

### **1️⃣ Clone the Repository**  
```sh
git clone https://github.com/yourusername/waste-management-system.git
cd waste-management-system
```

### **2️⃣ Create a Virtual Environment**  
To prevent dependency conflicts, create and activate a **Python 3.9 virtual environment**:  
```sh
python3.9 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```

### **3️⃣ Install Backend Dependencies**  
```sh
pip install -r requirements.txt
```

### **4️⃣ Set Up Frontend (React)**  
```sh
cd frontend
npm install
npm run build
cd ..
```

### **5️⃣ Start the Flask Backend**  
```sh
python backend.py
```
Visit **`http://127.0.0.1:5000/`** to access the application.

## 📡 API Endpoints  
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Upload an image and classify waste |
| `POST` | `/api/predict_video` | Upload a video and classify waste per frame |
| `GET` | `/api/stats` | Get waste classification statistics |
| `GET` | `/api/trends` | Get monthly waste trends |
| `POST` | `/api/send_report` | Send waste classification reports via email |

## 🔐 Environment Variables  
Create a `.env` file for **SMTP email settings**:  
```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

## 🛠️ Deployment  
For **Production Deployment**, use:  
```sh
gunicorn -w 4 -b 0.0.0.0:5000 backend:app
```
Use **NGINX** as a reverse proxy for Flask & React.  

## 👥 Contributors  
👨‍💻 **Your Name** – _Backend & AI_  
🎨 **Collaborator Name** – _Frontend UI/UX_  
💡 **Contributor Name** – _Data Visualization_  

## 📜 License  
📝 This project is licensed under the **MIT License** – feel free to use and modify!  

---

🌎 **Together, we can make the world a cleaner place!** ♻️  
⭐ Don't forget to **star** this repository! 🚀  

---

[📺 Watch the Demo Video](https://jsquads-my.sharepoint.com/:v:/g/personal/jsquads_jsquads_onmicrosoft_com/EZhYlcncjmhOpOnUWCsfB1sBKYFwjaUGPZHb8fNmpgjiiw?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=kiBbJj)



