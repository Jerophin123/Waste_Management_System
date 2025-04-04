# 🗑️ Waste Management System 🚀  

## 🌎 About the Project  
The **Waste Management System (WMS)** is an **AI-powered waste classification** platform that classifies waste as **Bio-Degradable** or **Non-Bio-Degradable** using **Deep Learning**.  
It includes **real-time image classification, video waste analysis, waste tracking, data visualization, chatbot assistance, and automated reporting** for an **eco-friendly waste disposal approach**.  

---

## 🎯 **Key Features**  

✅ **Real-time Waste Classification** – Predicts waste type using an AI model  
✅ **Webcam-based Detection** – Classify waste using a **live camera feed**  
✅ **Video Waste Processing** – Extracts frames and classifies waste in videos  
✅ **Interactive Dashboard** – Displays **waste trends, analytics & reports**  
✅ **PDF & CSV Reports** – Download waste reports in multiple formats  
✅ **Google Sheets & Drive Integration** – Auto-stores data & uploads files  
✅ **AI Chatbot Assistance** – Answers waste-related queries dynamically  
✅ **Email Notifications** – Send waste classification reports via email  
✅ **RESTful API** – Provides endpoints for classification, statistics & reports  

---

## 🏗️ **Tech Stack**  

🔹 **Frontend:** React.js, Material-UI, Framer Motion, Chart.js, React Webcam  
🔹 **Backend:** Flask, TensorFlow, Keras, OpenCV  
🔹 **Database:** MySQL  
🔹 **Visualization:** ReportLab, Matplotlib  
🔹 **Email Notifications:** SMTP, Python Email API  

---

## ⚠️ **Python & Node.js Requirements**  

Ensure you have the following installed:  

🟢 **Python 3.9**  
🟢 **Node.js 16+**  

Check your Python version:  
```sh
python --version
```
Check your Node.js version:  
```sh
node -v
```
If missing, download from:  
- [Python 3.9](https://www.python.org/downloads/release/python-390/)  
- [Node.js](https://nodejs.org/)  

---

## 🚀 **Getting Started**  

### **1️⃣ Clone the Repository**  
```sh
git clone https://github.com/yourusername/waste-management-system.git
cd waste-management-system
```

### **2️⃣ Set Up the Backend (Flask & AI Model)**  
Create a virtual environment:  
```sh
python3.9 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```
Install dependencies:  
```sh
pip install -r requirements.txt
```
Start the Flask backend:  
```sh
python backend.py
```
The server runs at **`http://127.0.0.1:5000/`**.

---

### **3️⃣ Set Up the Frontend (React.js)**  
Navigate to the frontend folder:  
```sh
cd frontend
npm install
npm start
```
The React app runs at **`http://localhost:3000/`**.

---

## 📡 **API Endpoints**  

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Upload an image and classify waste |
| `POST` | `/api/realtime_predict` | Predict waste in real-time from webcam |
| `POST` | `/api/predict_video` | Upload a video and classify frames |
| `GET` | `/api/stats` | Get waste classification statistics |
| `GET` | `/api/trends` | Get monthly waste trends |
| `POST` | `/api/send_report` | Send waste classification reports via email |
| `GET` | `/api/download_report` | Download a structured **PDF waste report** |
| `GET` | `/api/download_logs` | Download waste classification logs as **CSV** |

---

## 🔐 **Environment Variables (`.env` File)**  

Create a `.env` file in the root directory and add the following:  
```ini
# 📩 SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# 📊 Google Sheets & Drive Integration
GOOGLE_SHEETS_CREDS=credentials.json
GOOGLE_DRIVE_CREDS=drive_credentials.json
PARENT_FOLDER_ID=your-folder-id
FOLDER_BIO=bio-folder-id
FOLDER_NONBIO=nonbio-folder-id

# 🔌 MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DB=waste_management
```

---

## 💬 **Chatbot AI Assistance**  

The chatbot provides:  
✅ **System Overview & Features**  
✅ **Waste Classification Guide**  
✅ **Live Waste Data Retrieval**  
✅ **PDF & CSV Report Downloads**  
✅ **Smart Waste Disposal Tips**  
✅ **Email Notifications & Troubleshooting**  

Activate chatbot via the floating **💬 Chat Icon** in the app.

---

## 🛠 **Deployment**  

### **🔹 Deploy Backend (Flask)**
Use **Gunicorn** for production:  
```sh
gunicorn -w 4 -b 0.0.0.0:5000 backend2:app
```
Use **NGINX** as a reverse proxy for Flask.

### **🔹 Deploy Frontend (React)**
Use **Vercel / Netlify / Firebase Hosting**:
```sh
npm run build
```
Then deploy the **`frontend/build`** folder.

---

## 🎯 **How to Use the System?**  

### 📸 **Image Prediction**
1. Go to the **Prediction Page**.
2. **Upload an image** or **Enter a Google Drive link**.
3. Click **Predict**.
4. AI classifies the waste & shows confidence scores.
5. **If an email is provided, the classification result will be sent to your email.**

### 📷 **Real-time Webcam Classification**
1. Switch to **Camera Mode**.
2. Select the desired **camera device**.
3. Click **Start Real-Time** to begin predictions in real-time.
4. Click **capture button** to capture waste image.
5. AI classifies the waste & shows confidence scores. 
6. **If an email is provided, the classification result will be sent to your email.**

### 🎥 **Video Analysis**
1. Upload a **video file** or provide a **Google Drive link**.
2. Click **Predict** and wait for frame extraction.
3. View the **classified frames** in the results dialog.
4. **If an email is provided, the classification result will be sent to your email.**

### 📊 **Data & Reports**
1. **Dashboard** → View **live statistics & waste trends**.
2. **Logs Page** → View **past waste records**.
3. **Reports** → Download **CSV or PDF reports**.
4. **Email Reports** → Send reports via email.

---

## 🏆 **Why Use This System?**
✔ **AI-powered Waste Classification**  
✔ **Optimized for Speed & Accuracy**  
✔ **Real-time Predictions & Trend Analysis**  
✔ **Data Storage in Google Sheets & Drive**  
✔ **Automated Email Reports**  
✔ **User-friendly Chatbot Integration**  
✔ **Dark & Light Mode Theming**  


---

## 📜 **License**  
📝 This project is licensed under the **MIT License** – feel free to use and modify!  

---

## ⭐ **Support the Project!**
If you like this project, don’t forget to **🌟 star** the repository on GitHub! 🚀  
Together, we can make waste management **smarter & eco-friendly**! ♻️  

---
