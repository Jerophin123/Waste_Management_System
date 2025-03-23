from flask import Flask, request, jsonify
from keras.models import load_model
from keras.layers import DepthwiseConv2D
from PIL import Image, ImageOps
import numpy as np
import os
import cv2
import pymysql
from datetime import datetime
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
from flask import send_from_directory
from flask import Response
from flask import Flask, render_template
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.colors import Color
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.colors import Color
from reportlab.platypus import Paragraph
from google.cloud import translate_v2 as translate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
import csv
import io
import smtplib
import threading
import os
import re
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import mimetypes
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') 
from email.message import EmailMessage
from flask import Flask, send_from_directory, render_template
from werkzeug.utils import secure_filename
from flask import request, jsonify, send_file
import base64
from dotenv import load_dotenv

# ✅ Enable Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Load environment variables from .env file
load_dotenv()

# ✅ Read SMTP & Google API credentials from .env
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # Default to 587 if not set
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS")
GOOGLE_DRIVE_CREDS = os.getenv("GOOGLE_DRIVE_CREDS")

PARENT_FOLDER_ID = os.getenv("PARENT_FOLDER_ID")
FOLDER_BIO = os.getenv("FOLDER_BIO")
FOLDER_NONBIO = os.getenv("FOLDER_NONBIO")

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

# Initialize Flask app
frontend_build_path = os.path.abspath("./frontendbuild")

app = Flask(__name__, static_folder=frontend_build_path, template_folder=frontend_build_path)
CORS(app)  # Enable CORS for cross-origin requests
CORS(app, resources={r"/processed_frames/*": {"origins": "*"}})


UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed_frames"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER

DB_PATH = "waste_management.db"


# ✅ Google Sheets Authentication
def authenticate_google_sheets(creds_file):
    try:
        if not creds_file:
            raise ValueError("❌ Google Sheets credentials file path is missing in .env")

        if not os.path.exists(creds_file):
            raise FileNotFoundError(f"❌ Google Sheets credentials file not found: {creds_file}")

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            creds_file,
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"],
        )
        client = gspread.authorize(creds)

        try:
            sheet = client.open("wms").sheet1  # Replace "wms" with your actual Google Sheet name
        except gspread.SpreadsheetNotFound:
            raise Exception("❌ Google Sheet 'wms' not found. Check if the sheet name is correct.")

        print("✅ Successfully authenticated with Google Sheets!")  # Explicitly print
        logging.info("✅ Successfully authenticated with Google Sheets!")
        return sheet
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")  # Explicitly print
        logging.error(f"❌ Error connecting to Google Sheets: {e}")
        return None


# ✅ Google Drive Authentication
def authenticate_google_drive(creds_file):
    try:
        if not creds_file:
            raise ValueError("❌ Google Drive credentials file path is missing in .env")

        if not os.path.exists(creds_file):
            raise FileNotFoundError(f"❌ Google Drive credentials file not found: {creds_file}")

        gauth = GoogleAuth()
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            creds_file, ["https://www.googleapis.com/auth/drive"]
        )

        drive = GoogleDrive(gauth)
        print("✅ Successfully authenticated with Google Drive!")  # Explicitly print
        logging.info("✅ Successfully authenticated with Google Drive!")
        return drive
    except Exception as e:
        print(f"❌ Google Drive Authentication Failed: {e}")  # Explicitly print
        logging.error(f"❌ Google Drive Authentication Failed: {e}")
        return None


# ✅ Initialize Google Sheets & Drive Authentication
sheet = authenticate_google_sheets(GOOGLE_SHEETS_CREDS)
drive = authenticate_google_drive(GOOGLE_DRIVE_CREDS)

# ✅ Force print authentication status
if sheet:
    print("✅ Google Sheets is READY!")
else:
    print("❌ Google Sheets authentication FAILED!")

if drive:
    print("✅ Google Drive is READY!")
else:
    print("❌ Google Drive authentication FAILED!")

# Advanced chatbot responses (Enhanced with Backend, Frontend, and Usage Knowledge)
CHATBOT_RESPONSES = {
    "hello": [
        "<p>Hello! How can I assist you with the <b>Waste Management System</b>?</p>",
        "<p>Hi there! Need help with <b>WMS</b>?</p>",
        "<p>Hey! How can I help you today?</p>"
    ],
    "system_overview": [
        "<p>The <b>Waste Management System (WMS)</b> is an AI-powered platform that classifies waste as "
        "<b>Bio-Degradable</b> or <b>Non-Bio-Degradable</b> using Machine Learning.</p>"
        "<p>It includes a <b>React frontend</b> and a <b>Flask backend</b> that processes predictions and maintains records.</p>"
        "<p>Users can <b>upload images</b>, use <b>real-time webcam detection</b>, and analyze waste in videos.</p>"
        "<p>The system also provides <b>data analytics, reports, and trends</b> to help in better waste segregation.</p>"
    ],
    "backend_functionality": [
        "<p>The <b>backend</b> is built with <b>Flask (Python)</b> and handles <b>image classification, API requests, database storage, and analytics</b>.</p>"
        "<p>It uses a <b>Keras-based AI model</b> with <b>DepthwiseConv2D</b> to predict waste type.</p>"
        "<p>The database (<b>SQLite</b>) stores all waste records including <b>filename, type, confidence score, and timestamp</b>.</p>"
        "<p><b>API Endpoints</b> provide access to <b>waste statistics, trends, logs, and reports</b>.</p>"
        "<p>It also includes <b>real-time image processing, video frame analysis, and automated email reports</b>.</p>"
    ],
    "frontend_structure": [
        "<p>The <b>frontend</b> is built using <b>React.js</b> with <b>Material-UI</b> & <b>Framer Motion</b> for an interactive UI.</p>"
        "<p>It includes <b>Dark & Light mode</b> support, animated transitions, and a floating chatbot.</p>"
        "<p><b>Key Features:</b></p>"
        "<ul>"
        "<li><b>Dashboard:</b> Displays waste statistics, trends, and progress.</li>"
        "<li><b>Prediction Page:</b> Allows <b>image upload, webcam classification, and video processing</b>.</li>"
        "<li><b>Logs Page:</b> Stores past records, allows <b>report downloads</b> and <b>email reports</b>.</li>"
        "<li><b>Chatbot:</b> Provides assistance and guides users on waste classification.</li>"
        "</ul>"
    ],
    "how_to_use": [
        "<p><b>To classify waste:</b></p>"
        "<ul>"
        "<li>Go to the <b>Prediction Page</b> and choose <b>Image Upload</b> or <b>Camera Mode</b>.</li>"
        "<li>Click <b>Upload</b> or <b>Capture</b>, and the system will classify the waste as <b>Bio-Degradable</b> or <b>Non-Bio-Degradable</b>.</li>"
        "</ul>"
        "<p><b>For video analysis:</b></p>"
        "<ul>"
        "<li>Upload a <b>video file</b> on the <b>Prediction Page</b>, and the system will extract frames and classify them.</li>"
        "</ul>"
        "<p><b>To analyze waste trends:</b></p>"
        "<ul>"
        "<li>Visit the <b>Dashboard</b> for <b>Pie Charts, Bar Charts, and Line Graphs</b> showing waste distribution over time.</li>"
        "</ul>"
    ],
    "logs": [
        "<p>📜 <b>Logs Section:</b> The system maintains a record of all waste classifications.</p>",
        "<p>You can view past logs in the <b>'Logs'</b> tab, which includes <b>filename, waste type, confidence score, and timestamp</b>.</p>"
        "<p>Logs help track historical waste segregation and improve classification efficiency.</p>"
    ],
    "records": [
        "<p>📝 <b>Viewing Past Records:</b> The system saves all classified waste records in a database.</p>",
        "<p>Go to the <b>'Logs'</b> tab to check previous predictions along with <b>confidence scores</b>.</p>",
        "<p>Each record includes the <b>date, file name, waste type, and prediction confidence</b>.</p>"
    ],
   "download_report": [
        "<p>📥 <b>Downloading Reports:</b> You can generate a report summarizing waste classification data.</p>",
        "<p>Click <b>'Generate Report'</b> on the <b>'Logs'</b> page to create a detailed <b>PDF</b>.</p>",
        "<p>The report includes <b>classification trends, analytics, and waste distribution insights</b>.</p>"
    ],
    "csv_logs": [
        "<p>📊 <b>Exporting Logs as CSV:</b> You can download past logs in a structured <b>CSV</b> format.</p>",
        "<p>Click <b>'Download Logs'</b> on the <b>'Logs'</b> page to get a CSV file.</p>",
        "<p><b>CSV</b> files can be opened in <b>Excel, Google Sheets</b>, or any data analysis tool.</p>"
    ],
    "pdf_reports": [
        "<p>📄 <b>Generating PDF Reports:</b> You can get a detailed <b>PDF</b> report with charts and analytics.</p>",
        "<p>Click <b>'Generate Report'</b> in the <b>'Logs'</b> tab to create a structured report.</p>",
        "<p>The <b>PDF</b> includes <b>statistics, bar charts, and pie charts</b> of waste distribution.</p>"
    ],
    "how_to_get_logs": [
        "<p>🔍 <b>How to Retrieve Logs?</b></p>",
        "<ol>",
        "<li>Go to the <b>'Logs'</b> section to view all past records.</li>",
        "<li>Click <b>'Download Logs'</b> to get a <b>CSV</b> file.</li>",
        "<li>Click <b>'Generate Report'</b> to create a <b>PDF</b>.</li>",
        "<li>You can also filter records by <b>date, month, or year</b> for better insights.</li>",
        "</ol>"
    ],
    "real_time_prediction": [
        "<p>✅ Yes, you can classify waste in <b>real-time</b> using your webcam.</p>"
        "<p>Go to the <b>Prediction Page</b>, switch to <b>Camera Mode</b>, and click <b>Start Real-Time</b>.</p>"
        "<p>The system will continuously classify waste and display the <b>confidence scores</b> for <b>Bio-Degradable</b> & <b>Non-Bio-Degradable</b>.</p>"
        "<p>🔊 You will also get <b>audio alerts</b> when confidence reaches <b>100%</b>.</p>"
    ],
    "deployment": [
        "<p>🚀 <b>How to Deploy WMS?</b></p>"
        "<ul>"
        "<li>To deploy <b>WMS locally</b>, install <b>Flask, React.js, SQLite, and TensorFlow</b>.</li>"
        "<li>For <b>cloud hosting</b>, deploy the backend on <b>AWS, Google Cloud, or Azure</b> using <b>Docker</b> or a <b>virtual machine</b>.</li>"
        "<li>The frontend can be deployed on <b>Vercel, Netlify, or Firebase Hosting</b>.</li>"
        "<li>For <b>scalability</b>, replace <b>SQLite</b> with <b>PostgreSQL</b> and use <b>Redis</b> for caching frequent API calls.</li>"
        "</ul>"
    ],
    "waste_collected": [
        "You can check the waste collected over a specific period by specifying the date range.",
        "I can provide details about waste collected on a specific day, time, or within a given range. Just ask!",
        "To check waste collection data, specify a time period like 'How much waste was collected today?' or 'Show me waste stats for January 2025'."
    ],
    "waste_on_date": [
        "<p>📅 <b>Check Waste Collected on a Specific Date:</b></p>"
        "<p>Specify a date to check the waste collected. Example: <b>'Show me the waste collected on 2025-02-20'</b>.</p>"
        "<p>You can ask, <b>'How much waste was collected on March 1, 2025?'</b></p>"
        "<p>Enter a specific date, and I will fetch the waste data for that day.</p>"
    ],
    "waste_in_time_range": [
        "<p>⏳ <b>Check Waste Collected Within a Specific Time Range:</b></p>"
        "<p>To check waste collection within a specific time range, ask like this: <b>'How much waste was collected between 10 AM and 5 PM today?'</b></p>"
        "<p>You can filter waste records by a custom time range. Just specify start and end times!</p>"
        "<p>Try asking: <b>'Show waste collected between 6 PM and 9 PM on 2025-02-19'</b>.</p>"
    ],
    "bio_nonbio_waste": [
        "<p>♻ <b>Check Bio-Degradable & Non-Bio-Degradable Waste:</b></p>"
        "<p>I can fetch how much <b>bio</b> and <b>non-bio</b> waste was collected within a specific period.</p>"
        "<p>Try asking, <b>'How much bio and non-bio waste was collected today?'</b></p>"
        "<p>For category-wise segregation, specify the type and duration, e.g., <b>'Show non-bio waste collected this week'</b>.</p>"
    ],
    "waste_on_weekday": [
        "<p>📆 <b>Check Waste Collected on a Specific Weekday:</b></p>"
        "<p>I can fetch waste collected on any weekday. Try asking: <b>'How much waste was collected last Monday?'</b></p>"
        "<p>Specify a weekday (<b>Sunday to Saturday</b>), and I'll fetch waste data for that day.</p>"
        "<p>Try: <b>'Show me the waste collected on Wednesday'</b> or <b>'What was the waste collected last Friday?'</b></p>"
    ],
    "troubleshooting": [
        "<p>⚙️ <b>Troubleshooting Guide:</b></p>"
        "<p><b>If the AI model isn't working:</b></p>"
        "<ul>"
        "<li>Ensure the <code>keras_model.h5</code> file is in the correct directory.</li>"
        "<li>Check that you have installed <b>TensorFlow & Keras</b>.</li>"
        "<li>If using a custom model, ensure you define <code>DepthwiseConv2D</code> as a custom layer.</li>"
        "</ul>"
        "<p><b>If the Flask API crashes:</b></p>"
        "<ul>"
        "<li>Check if port <b>5000</b> is already in use with <code>netstat -ano | findstr :5000</code>.</li>",
        "<li>Run <code>flask run --port 5001</code> to change the port.</li>",
        "</ul>"
        "<p><b>If image uploads fail:</b></p>"
        "<ul>"
        "<li>Ensure the uploaded file is an image (<code>JPG</code>, <code>PNG</code>).</li>"
        "<li>Check Flask file size limits (<code>MAX_CONTENT_LENGTH</code>).</li>"
        "</ul>"
        "<p><b>If there's a database error:</b></p>"
        "<ul>"
        "<li>Delete <code>waste_management.db</code> and restart the backend (<code>init_db()</code> will recreate it).</li>"
        "</ul>"
    ],
    "security": [
        "<p>🔒 <b>Security Features in WMS:</b></p>"
        "<ul>"
        "<li>By default, WMS does not require authentication, but you can add <b>JWT (JSON Web Token)</b> authentication.</li>"
        "<li>To restrict access, modify the <b>Flask API</b> to require <b>API keys</b> for each request.</li>"
        "<li>For report security, ensure only <b>authorized users</b> receive report emails.</li>"
        "<li>To prevent database tampering, restrict API endpoints using <b>CORS policies</b> and <b>rate limiting</b>.</li>"
        "</ul>"
    ],
    "data_analysis": [
        "<p>📊 <b>Data Analysis & Insights:</b></p>"
        "<ul>"
        "<li>You can generate a detailed <b>PDF report</b> from the <b>Logs Page</b>.</li>"
        "<li>WMS offers <b>data analytics, charts, and trend analysis</b> in the <b>Dashboard</b>.</li>"
        "<li>For waste classification trends, WMS provides <b>Pie Charts, Bar Graphs, and Line Graphs</b>.</li>"
        "<li>To export logs, click <b>Download CSV</b>, which can be opened in <b>Excel</b>.</li>"
        "</ul>"
    ],
    "send_email": [
        "<p>📧 <b>Send Email Reports:</b> You can send a <b>waste management report</b> directly via email.</p>"
        "<p>To send a report, type: <b>'Send mail to example@gmail.com'</b></p>"
        "<p>Alternatively, go to the <b>'Logs'</b> tab and enter an email in the <b>'Send Report'</b> section.</p>"
        "<p>You can also upload a <b>.txt</b> file with multiple emails and send reports in bulk.</p>"
    ],
    "how_to_send_email": [
        "<p>📩 <b>How to Send Email Reports?</b></p>"
        "<ol>",
        "<li>The system will get the email and send the report.</li>"
        "<li>You can enter the email in the <b>'Logs'</b> tab.</li>"
        "<li>If you want to send to multiple people, upload a <b>.txt</b> file</b> with email addresses.</li>"
        "<li>📥 Check your inbox for the report!</li>"
        "</ol>"
    ],
    "total_waste": [
        "<p>📊 <b>Total Waste Collected:</b> The system tracks all waste items classified over time.</p>"
        "<p>You can check how much waste has been collected so far.</p>"
        "<p>Try asking: <b>'How much total waste has been collected?'</b></p>"
    ],
    "waste_percentage": [
        "<p>♻ <b>Bio vs Non-Bio Waste Distribution:</b> This helps understand how much of the waste is <b>biodegradable</b> vs <b>non-biodegradable</b>.</p>",
        "<p>You can ask for the <b>percentage of waste</b> collected as bio and non-bio.</p>"
        "<p>Try asking: <b>'What is the percentage of bio and non-bio waste?'</b></p>"
    ],
    "waste_trend": [
        "<p>📈 <b>Waste Classification Trend Over Time:</b> The system tracks the number of classified waste items each month.</p>"
        "<p>You can check how <b>waste collection trends</b> over time.</p>"
        "<p>Try asking: <b>'Show me waste trends over the last few months.'</b></p>"
    ],
    "waste_trend_specific_month": [
        "<p>📈 <b>Monthly Waste Trend:</b> You can check how much waste was collected in a <b>specific month and year</b>.</p>"
        "<p>Try asking: <b>'Waste trend in January 2025'</b> or <b>'Waste collected in March 2024'</b>.</p>"
    ],
    "generate_report": [
        "<p>📄 <b>Generating your Waste Management Report...</b> Please wait.</p>"
        "<p>✅ <b>Report generation started.</b> You will receive a download link shortly.</p>"
        "<p>📝 <b>Creating your detailed report.</b> It will be available for download soon!</p>"
    ],
    "waste_management_best_practices": [
        "<p>♻ <b>Best Practices for Waste Management:</b></p>"
        "<ol>"
        "<li>1️⃣ Always <b>segregate waste</b> into <b>bio-degradable</b> and <b>non-bio-degradable</b> categories.</li>"
        "<li>2️⃣ Reduce <b>single-use plastics</b> and opt for reusable alternatives.</li>"
        "<li>3️⃣ Compost kitchen waste like <b>fruit peels, vegetable scraps, and coffee grounds</b>.</li>"
        "<li>4️⃣ Dispose of <b>hazardous waste</b> (batteries, e-waste) properly to avoid contamination.</li>"
        "<li>5️⃣ Participate in local <b>recycling programs</b> for paper, glass, and plastics.</li>"
        "<li>6️⃣ Encourage <b>zero-waste initiatives</b> at home and workplaces.</li>"
        "<li>7️⃣ Use <b>waste classification AI</b> to improve waste processing efficiency.</li>"
        "<li>8️⃣ Minimize food waste by <b>donating excess food</b> to food banks.</li>"
        "</ol>"
    ],
    # 🔹 DETAILED WASTE CLASSIFICATION GUIDELINES
    "bio_vs_nonbio_detailed": [
        "<p>♻ <b>Understanding Bio-Degradable & Non-Bio-Degradable Waste</b></p>"
        "<p>🟢 <b>Bio-Degradable Waste:</b> Can be decomposed naturally and is eco-friendly.</p>"
        "<ul>"
        "<li><b>Examples:</b> Food scraps, paper, wood, cotton, natural fabric.</li>"
        "<li><b>Disposal:</b> Composting, Organic Waste Management.</li>"
        "</ul>"
        "<p>🚯 <b>Non-Bio-Degradable Waste:</b> Does not break down easily and can harm ecosystems.</p>"
        "<ul>"
        "<li><b>Examples:</b> Plastics, metals, glass, electronic waste.</li>"
        "<li><b>Disposal:</b> Recycling, Special Waste Treatment Facilities.</li>"
        "</ul>"
        "<p>🔄 <b>Key Tip:</b> Always separate <b>bio & non-bio waste</b> at the source for effective waste management!</p>"
    ],
    # 🔹 COMPOSTING GUIDE
    "composting_guide": [
        "<p>🌱 <b>Composting Guide: Convert Kitchen Waste into Fertilizer!</b></p>"
        "<ol>"
        "<li>1️⃣ Collect <b>fruit & vegetable peels, eggshells, coffee grounds</b>.</li>"
        "<li>2️⃣ Avoid adding <b>meat, dairy, and oily foods</b> to compost.</li>"
        "<li>3️⃣ Mix <b>dry materials</b> (leaves, shredded paper) for a good balance.</li>"
        "<li>4️⃣ Keep it <b>moist but not too wet</b> to allow microbial activity.</li>"
        "<li>5️⃣ Turn the compost pile <b>every few days</b> to speed up decomposition.</li>"
        "<li>6️⃣ Within a few weeks, you'll have <b>rich organic fertilizer</b> for your garden!</li>"
        "</ol>"
    ],
    # 🔹 RECYCLING TIPS
    "recycling_tips": [
        "<p>♻ <b>Recycling Do’s and Don’ts:</b></p>"
        "<ul>"
        "<li>✅ <b>DO:</b> Rinse out bottles & cans before recycling.</li>"
        "<li>✅ <b>DO:</b> Separate paper, plastic, and metal waste.</li>"
        "<li>✅ <b>DO:</b> Flatten cardboard boxes to save space.</li>"
        "<li>❌ <b>DON’T:</b> Recycle dirty or greasy food containers (like pizza boxes).</li>"
        "<li>❌ <b>DON’T:</b> Mix hazardous waste (batteries, electronics) with regular trash.</li>"
        "</ul>"
        "<p>💡 <b>Tip:</b> Always check your local recycling guidelines for the best practices!</p>"
    ],

    # 🔹 GOVERNMENT & ENVIRONMENTAL REGULATIONS
    "government_regulations": [
        "<p>🌍 <b>Environmental Regulations on Waste Management:</b></p>"
        "<ol>"
        "<li>1️⃣ Governments enforce <b>strict laws</b> on waste disposal to reduce pollution.</li>"
        "<li>2️⃣ Companies must comply with <b>eco-friendly waste disposal guidelines</b>.</li>"
        "<li>3️⃣ Many countries <b>ban single-use plastics</b> to cut down on plastic waste.</li>"
        "<li>4️⃣ Some regions <b>charge fines</b> for improper waste disposal.</li>"
        "<li>5️⃣ <b>Recycling incentives</b> are offered in many places – check with your local authorities!</li>"
        "</ol>"
        "<p>🌱 <b>Protect the planet</b> by following responsible waste management laws!</p>"
    ],

    # 🔹 AI MODEL EXPLANATION
    "ai_model_explanation": [
        "<p>🤖 <b>How does the AI model work?</b></p>"
        "<ol>"
        "<li>1️⃣ The model is built using <b>Keras (TensorFlow)</b> with a <b>DepthwiseConv2D CNN</b> architecture.</li>"
        "<li>2️⃣ It processes images and predicts whether the waste is <b>bio-degradable</b> or <b>non-bio-degradable</b>.</li>"
        "<li>3️⃣ Uses <b>224x224 pixel images</b> as input, normalizes them, and runs inference.</li>"
        "<li>4️⃣ The prediction is based on <b>confidence scores</b> for each waste category.</li>"
        "<li>5️⃣ <b>Continuous Learning:</b> The model improves over time with new training data.</li>"
        "</ol>"
        "<p>💡 <b>AI-powered waste classification</b> helps in <b>efficient & smart waste disposal!</b></p>"
    ],

    # 🔹 ADVANCED TROUBLESHOOTING
    "advanced_troubleshooting": [
        "<p>⚠ <b>Troubleshooting Common Issues:</b></p>"
        "<p>🛠 <b>Flask Server Issues:</b></p>"
        "<ul>"
        "<li>Run <code>flask run --port 5001</code> if port 5000 is occupied.</li>"
        "<li>Check if <code>waste_management.db</code> is accessible.</li>"
        "</ul>"
        "<p>🔧 <b>Model Prediction Errors:</b></p>"
        "<ul>"
        "<li>Ensure <code>keras_model.h5</code> exists in the correct directory.</li>"
        "<li>Run <code>pip install tensorflow keras opencv-python</code> to install dependencies.</li>"
        "</ul>",
        "<p>📂 <b>File Upload Issues:</b></p>"
        "<ul>"
        "<li>Ensure uploaded files are in supported formats (<code>.jpg</code>, <code>.png</code>, <code>.mp4</code>).</li>"
        "<li>If files don’t upload, check Flask’s <code>UPLOAD_FOLDER</code> path.</li>"
        "</ul>"
    ],

    # 🔹 REPORT GENERATION & CSV EXPLANATION
    "report_csv_details": [
        "<p>📄 <b>Understanding Reports & CSV Logs:</b></p>"
        "<p>✅ <b>The PDF report contains:</b></p>"
        "<ul>",
        "<li>📜 <b>Classification logs</b></li>"
        "<li>📊 <b>Waste segregation statistics</b></li>"
        "<li>📈 <b>Pie & Bar Charts</b> showing waste trends.</li>"
        "</ul>",
        "<p>📊 <b>CSV Logs:</b></p>"
        "<ul>",
        "<li>📂 Download <b>CSV logs</b> to view raw data.</li>"
        "<li>📊 Open CSV files in <b>Excel/Google Sheets</b> for analysis.</li>"
        "</ul>",
        "<p>📥 <b>Download options:</b> Click <b>‘Download Logs’</b> or <b>‘Generate Report’</b> in the <b>Logs</b> tab.</p>"
    ],

    "waste_trends_insights": [
        "<p>📊 <b>Waste Collection Trends & Insights:</b></p>"
        "<ol>",
        "<li>1️⃣ <b>Monthly trends</b> show seasonal variations in waste disposal.</li>"
        "<li>2️⃣ A high <b>non-bio-degradable percentage</b> may indicate plastic overuse.</li>"
        "<li>3️⃣ Sudden <b>spikes in waste data</b> may indicate festivals or public events.</li>"
        "<li>4️⃣ <b>Long-term data</b> helps predict future waste trends.</li>"
        "</ol>",
        "<p>📈 <b>Check the Dashboard</b> for real-time analytics!</p>"
    ],

    # 🔹 SMART WASTE DISPOSAL SOLUTIONS
    "smart_waste_solutions": [
        "<p>💡 <b>Smart Waste Disposal Solutions:</b></p>"
        "<ul>",
        "<li>✅ <b>AI-based waste bins</b> automatically sort waste into <b>bio/non-bio</b> categories.</li>"
        "<li>✅ <b>IoT Sensors</b> detect waste levels in bins and optimize garbage collection routes.</li>"
        "<li>✅ <b>Reverse Vending Machines</b> allow users to recycle plastic bottles for rewards.</li>"
        "</ul>",
        "<p>🌍 <b>Technology is transforming waste management – be a part of the change!</b></p>"
    ],

    "enhanced_patterns": [
        "<p>💬 <b>You can ask things like:</b></p>",
        "<ul>",
        "<li>❓ <b>How to predict waste?</b></li>",
        "<li>🖼️ <b>Can I classify images?</b></li>",
        "<li>📈 <b>Show me waste trends</b></li>",
        "<li>📜 <b>Where can I see past logs?</b></li>",
        "<li>📧 <b>Send report to my email</b></li>",
        "<li>🤖 <b>How does the AI model work?</b></li>",
        "<li>🗄️ <b>What is the database used?</b></li>",
        "<li>📊 <b>Can I get a CSV log?</b></li>",
        "</ul>"
    ],

    "default": [
        "<p>🤔 I'm not sure how to answer that. Please rephrase your question or refer to the documentation.</p>",
        "<p>❓ I don't understand that yet. Try asking something else about <b>WMS</b>!</p>"
    ]

}

# Define patterns to recognize user questions in different ways
PATTERN_RESPONSES = {
    r"(?i)\b(hi|hello|hey)\b": "hello",
    r"(?i)\b(waste management system|explain wms|tell me about this project|how does this system work)\b": "system_overview",
    r"(?i)\b(backend|server|flask|database|model|api|how does the backend work)\b": "backend_functionality",
    r"(?i)\b(frontend|ui|react|dashboard|features|how does the frontend work)\b": "frontend_structure",
    r"(?i)\b(how to use|usage|how do i use this system|how can i classify waste)\b": "how_to_use",
    r"(?i)\b(logs)\b": "logs",
    r"(?i)\b(records)\b": "records",
    r"(?i)\b(download report)\b": "download_report",
    r"(?i)\b(csv|export csv|download logs)\b": "csv_logs",
    r"(?i)\b(pdf|generate pdf|waste report)\b": "pdf_reports",
    r"(?i)\b(generate report|download report|get pdf report|create report)\b": "generate_report",
    r"(?i)\b(how to get logs|retrieve logs|fetch logs)\b": "how_to_get_logs",
    r"(?i)\b(send email|email report|mail report|send waste report|email|emails)\b": "send_email",
    r"(?i)\b(how to send email|email process|how to mail report)\b": "how_to_send_email",
    r"(?i)\b(email sent|status of email|report email status)\b": "email_status",
    r"(?i)\b(waste collected|waste data|how much waste)\b": "waste_collected",
    r"(?i)\b(waste on \d{4}-\d{2}-\d{2}|waste collected on)\b": "waste_on_date",
    r"(?i)\b(waste between \d{1,2} (AM|PM) and \d{1,2} (AM|PM)|waste in time range|waste during)\b": "waste_in_time_range",
    r"(?i)\b(bio waste|non-bio waste|segregation data|bio and non-bio waste collected)\b": "bio_nonbio_waste",
    r"(?i)\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b": "waste_on_weekday",
    r"(?i)\b(email failed|could not send email|email error|why is email not sent)\b": "email_error",
    r"(?i)\b(real-time|live|webcam|camera|how does real-time prediction work)\b": "real_time_prediction",
    r"(?i)\b(predict waste|classify images|show trends|get logs|email report|ai model|database|csv log)\b": "enhanced_patterns",
    r"(?i)\b(deploy|installation|hosting|how to run)\b": "deployment",
    r"(?i)\b(waste management tips|waste handling|best practices)\b": "waste_management_best_practices",
    r"(?i)\b(composting|how to compost|food waste compost)\b": "composting_guide",
    r"(?i)\b(recycling|how to recycle|recycling tips)\b": "recycling_tips",
    r"(?i)\b(government rules|waste regulations|laws on waste)\b": "government_regulations",
    r"(?i)\b(how does ai work|ai model|machine learning model)\b": "ai_model_explanation",
    r"(?i)\b(report details|csv logs|how to read reports)\b": "report_csv_details",
    r"(?i)\b(trends insights|waste trends|data analytics)\b": "waste_trends_insights",
    r"(?i)\b(smart waste|waste technology|ai for waste)\b": "smart_waste_solutions",
    r"(?i)\b(troubleshoot|fix errors|debugging issues)\b": "advanced_troubleshooting",
    r"(?i)\b(error|crash|not working|troubleshoot|debug)\b": "troubleshooting",
    r"(?i)\b(security|authentication|restrict access|protect data)\b": "security",
    r"(?i)\b(analytics|report|data visualization|trends)\b": "data_analysis",
    r"(?i)\b(total waste|how much total waste|total waste collected)\b": "total_waste",
    r"(?i)\b(bio vs non-bio|percentage of bio waste|waste percentage|bio and non-bio percentage)\b": "waste_percentage",
    r"(?i)\b(waste trend|trend over time|waste trends|classification trends)\b": "waste_trend",
    r"(?i)\b(waste trend in \w+ \d{4}|waste collected in \w+ \d{4})\b": "waste_trend_specific_month"
}



# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Database Connection Function
def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

# Initialize Database
def init_db():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255),
                waste_type VARCHAR(50),
                confidence FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

init_db()

# Custom DepthwiseConv2D to handle the 'groups' argument
class CustomDepthwiseConv2D(DepthwiseConv2D):
    def __init__(self, **kwargs):
        kwargs.pop("groups", None)  # Remove unsupported argument
        super().__init__(**kwargs)

# Paths to the model and labels file
model_path = "keras_model.h5"
labels_path = "labels.txt"

# Load the model with the custom DepthwiseConv2D layer
try:
    model = load_model(model_path, custom_objects={"DepthwiseConv2D": CustomDepthwiseConv2D})
    logging.info("Model loaded successfully!")
except Exception as e:
    logging.error(f"Error loading model: {e}")
    exit()

# Load the labels and map to friendly class names
try:
    class_names = [line.strip() for line in open(labels_path, "r").readlines()]
    friendly_classes = {str(index): label for index, label in enumerate(class_names)}
    logging.info("Labels loaded successfully!")
except Exception as e:
    logging.error(f"Error loading labels: {e}")
    exit()

def convert_google_drive_link(url):
    """
    Converts a Google Drive file link to a direct download link.
    """
    match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url  # Return original if not a Drive link

def download_image(image_url, filename):
    """
    Downloads an image from a URL (Google Drive/Photos) and ensures it's a valid image.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    image_url = convert_google_drive_link(image_url)  # Convert Drive link to direct link

    try:
        response = requests.get(image_url, headers=headers, stream=True)
        if response.status_code != 200:
            print(f"❌ Failed to download image. HTTP Status: {response.status_code}")
            return None

        # Read response content
        image_bytes = io.BytesIO(response.content)
        
        # Validate if it's a real image
        try:
            image = Image.open(image_bytes).convert("RGB")
        except Exception as e:
            print(f"❌ Error: File is not a valid image - {e}")
            return None

        # Save image with the provided filename
        temp_image_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(temp_image_path, format="JPEG")
        return temp_image_path

    except Exception as e:
        print(f"❌ Error downloading image: {e}")
        return None

def download_video(video_url, filename):
    """
    Downloads a video file from a URL and saves it locally.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    video_url = convert_google_drive_link(video_url)  # Convert Drive link to direct link

    try:
        response = requests.get(video_url, headers=headers, stream=True)
        if response.status_code != 200:
            print(f"❌ Failed to download video. HTTP Status: {response.status_code}")
            return None

        # Save the video locally
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(video_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        
        return video_path
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        return None

# Function to process and predict the image
def predict_image(image_path):
    """
    Processes the given image and predicts the confidence scores for bio and nonBio classes.

    Args:
        image_path (str): Path to the image file.

    Returns:
        dict: A dictionary containing confidence scores for bio and nonBio classes.
    """
    try:
        logging.info(f"Opening image at path: {image_path}")
        image = Image.open(image_path).convert("RGB")
        logging.info("Image opened successfully.")

        size = (224, 224)  # Model input size
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        logging.info("Image resized successfully.")

        image_array = np.asarray(image)
        logging.info(f"Image converted to array: {image_array.shape}")

        # Normalize the image
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
        logging.info(f"Image normalized.")

        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data[0] = normalized_image_array

        # Predict
        logging.info("Making prediction...")
        prediction = model.predict(data)[0]
        logging.info(f"Prediction results: {prediction}")

        # Return results
        return {
            "bio": float(prediction[0]),
            "nonBio": float(prediction[1])
        }
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return {"error": str(e)}


@app.route("/api/realtime_predict", methods=["POST"])
def realtime_predict():
    """
    Handles real-time image predictions sent from the frontend.

    Returns:
        JSON: Confidence scores for both bio and nonBio classes.
    """
    try:
        # Check if a file is included in the request
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Save the image temporarily
        temp_file_path = os.path.join(app.config["UPLOAD_FOLDER"], "temp_realtime.jpg")
        file.save(temp_file_path)

        # Perform the prediction
        result = predict_image(temp_file_path)

        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error during real-time prediction: {e}")
        return jsonify({"error": "An error occurred during real-time prediction."}), 500



def log_to_google_sheets(filename, waste_type, confidence):
    """
    Logs waste classification records to Google Sheets.

    Args:
        filename (str): Name of the file.
        waste_type (str): Classified waste type.
        confidence (float): Confidence score of classification.
    """
    if sheet:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([filename, waste_type, confidence, timestamp])
            print(f"✅ Logged to Google Sheets: {filename}, {waste_type}, {confidence}")
        except Exception as e:
            print(f"❌ Error logging to Google Sheets: {e}")

# Function to save prediction results in SQLite
def save_record(filename, waste_type, confidence):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO records (filename, waste_type, confidence, timestamp)
                VALUES (%s, %s, %s, NOW())
            ''', (filename, waste_type, confidence))
        conn.commit()
    except Exception as e:
        print(f"❌ Error saving record: {e}")
    finally:
        conn.close()


    log_to_google_sheets(filename, waste_type, confidence)

@app.route("/api/google_sheets_logs", methods=["GET"])
def get_google_sheets_logs():
    """
    Fetches logs from Google Sheets and returns them as JSON.
    """
    if not sheet:
        return jsonify({"error": "Google Sheets connection failed"}), 500

    try:
        data = sheet.get_all_records()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Error fetching logs from Google Sheets: {e}"}), 500


def upload_to_drive(filepath, waste_type, is_video_frame=False):
    """
    Uploads images or video frames to Google Drive in classified subfolders.

    Args:
        filepath (str): Path to image file.
        waste_type (str): "Bio-Degradable" or "Non-Bio-Degradable".
        is_video_frame (bool): True if the image is a video frame.

    Returns:
        str: Google Drive file link.
    """
    try:
        # Use separate Google Drive folders for video frames
        if is_video_frame:
            folder_id = FOLDER_BIO if waste_type == "Bio-Degradable" else FOLDER_NONBIO
        else:
            folder_id = FOLDER_BIO if waste_type == "Bio-Degradable" else FOLDER_NONBIO

        file_drive = drive.CreateFile({'title': os.path.basename(filepath), 'parents': [{'id': folder_id}]})
        file_drive.SetContentFile(filepath)
        file_drive.Upload()
        return f"https://drive.google.com/file/d/{file_drive['id']}/view"
    except Exception as e:
        logging.error(f"Google Drive Upload Error: {e}")
        return None


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Unified prediction function for both file uploads and Google Drive/Photos links.
    """
    try:
        image_path = None
        recipient_email = request.form.get("email")
        logging.info(f"📧 Email received: {recipient_email}")

        # Check if a file is uploaded
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400

            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            file.save(image_path)
            logging.info(f"✅ File saved temporarily at: {image_path}")

        # Check if a Google Drive/Photos link is provided
        elif "url" in request.json:
            image_url = request.json["url"]
            if not ("drive.google.com" in image_url or "photos.google.com" in image_url):
                return jsonify({"error": "Invalid Google Drive/Photos link."}), 400

            filename = f"image_from_link_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            image_path = download_image(image_url, filename)

            if not image_path:
                return jsonify({"error": "Failed to download image."}), 500

        else:
            return jsonify({"error": "No file or valid URL provided"}), 400

        # Ensure the file exists
        if not os.path.exists(image_path):
            return jsonify({"error": "File saving failed!"}), 500

        # Predict waste type using AI Model
        logging.info("🧠 Running waste classification model...")
        result = predict_image(image_path)
        logging.info(f"📊 Prediction result: {result}")

        if "error" in result:
            logging.error(f"❌ Prediction error: {result['error']}")
            return jsonify({"error": result["error"]}), 500

        # Determine waste classification
        waste_class = "Bio-Degradable" if result["bio"] > result["nonBio"] else "Non-Bio-Degradable"
        confidence_score = max(result["bio"], result["nonBio"])

        # ✅ Save Record in Database
        save_record(filename, waste_class, confidence_score)

        # ✅ Prepare Response
        response_data = {
            "class": waste_class,
            "bio": result["bio"],
            "nonBio": result["nonBio"],
            "confidence_score": confidence_score
        }
        logging.info(f"✅ Prediction saved: {response_data}")

        # ✅ Start background thread for Google Drive upload
        threading.Thread(target=upload_image_to_drive, args=(image_path, waste_class)).start()

        # ✅ Send Email in **Background Thread**
        if recipient_email:
            logging.info(f"📧 Sending result email in background to {recipient_email}")
            send_result_email_smtp_background(recipient_email, filename, waste_class, confidence_score)

        return jsonify(response_data)

    except Exception as e:
        logging.error(f"❌ Error processing file: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500



def upload_image_to_drive(image_path, waste_class):
    """
    Asynchronously uploads the image to Google Drive in the background.
    This ensures faster predictions by uploading the image separately.
    """
    try:
        logging.info(f"⏳ Uploading {image_path} to Google Drive...")
        google_drive_link = upload_to_drive(image_path, waste_class)
        logging.info(f"✅ Uploaded to Google Drive: {google_drive_link}")
    except Exception as e:
        logging.error(f"❌ Error uploading {image_path} to Google Drive: {e}")

    finally:
        # ✅ Remove Local Temporary File (after upload)
        if os.path.exists(image_path):
            os.remove(image_path)
            logging.info(f"🗑️ Local file {image_path} deleted.")


# Prediction Function
def predict_frame(image_path):
    image_data = preprocess_image(image_path)
    if image_data is None:
        return {"error": "Image processing failed"}

    prediction = model.predict(image_data)[0]
    return {
        "bio": float(prediction[0]),
        "nonBio": float(prediction[1])
    }


# Extract Frames from Video
def extract_frames(video_path, output_folder, frame_interval=30):
    frames = []
    cap = cv2.VideoCapture(video_path)
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # No more frames

        if frame_count % frame_interval == 0:
            frame_filename = os.path.join(output_folder, f"frame_{frame_count}.jpg")
            cv2.imwrite(frame_filename, frame)
            frames.append(frame_filename)  # Store only the file path

        frame_count += 1

    cap.release()
    return frames


@app.route("/api/predict_video", methods=["POST"])
def predict_video():
    """
    Unified function to predict waste from either a video file or a Google Drive link.
    """
    video_path = None  # Initialize video path variable

    try:
        recipient_email = request.form.get("email")  # ✅ Get recipient email
        logging.info(f"📧 Email received: {recipient_email}")

        # **1️⃣ Check if a file is uploaded**
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400

            # Save the uploaded video file
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            video_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(video_path)
            logging.info(f"📂 Video saved at: {video_path}")

        # **2️⃣ Check if a Google Drive link is provided**
        elif "url" in request.json:
            video_url = request.json["url"]

            # Validate Google Drive or Photos link
            if not ("drive.google.com" in video_url or "photos.google.com" in video_url):
                return jsonify({"error": "Invalid Google Drive/Photos link."}), 400

            # Generate a filename for the downloaded video
            filename = f"video_from_link_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"

            video_path = download_video(video_url, filename)
            if not video_path:
                return jsonify({"error": "Failed to download video."}), 500
            logging.info(f"✅ Video downloaded and saved at: {video_path}")

        else:
            return jsonify({"error": "No file or valid URL provided"}), 400

        # **3️⃣ Extract frames from the video**
        frames_folder = os.path.join(app.config["UPLOAD_FOLDER"], "frames")
        os.makedirs(frames_folder, exist_ok=True)
        frame_files = extract_frames(video_path, frames_folder, frame_interval=30)

        if not frame_files:
            logging.error("⚠️ No frames extracted from the video!")
            return jsonify({"error": "Failed to extract frames from video"}), 500

        predictions = []
        bio_count = 0
        non_bio_count = 0
        drive_upload_queue = []  # Store frames to upload later

        for frame_path in frame_files:
            logging.info(f"🖼 Processing frame: {frame_path}")
            result = predict_image(frame_path)

            if "error" in result:
                logging.warning(f"⚠️ Prediction failed for {frame_path}")
                continue

            # Classify waste type
            waste_class = "Bio-Degradable" if result["bio"] > result["nonBio"] else "Non-Bio-Degradable"
            confidence_score = max(result["bio"], result["nonBio"])

            # Count classification types
            if waste_class == "Bio-Degradable":
                bio_count += 1
            else:
                non_bio_count += 1

            # Save prediction to the database
            save_record(os.path.basename(frame_path), waste_class, confidence_score)

            # Add to upload queue (upload later in background)
            drive_upload_queue.append((frame_path, waste_class))

            # Load the frame for annotation
            frame = cv2.imread(frame_path)
            if frame is None:
                logging.warning(f"⚠️ Failed to read image {frame_path}")
                continue

            # Draw Prediction on Frame
            label = f"{waste_class} ({confidence_score:.2f})"
            color = (0, 255, 0) if waste_class == "Bio-Degradable" else (0, 0, 255)
            cv2.putText(frame, label, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # Save Processed Frame
            processed_frame_path = os.path.join(PROCESSED_FOLDER, os.path.basename(frame_path))
            cv2.imwrite(processed_frame_path, frame)
            logging.info(f"✅ Processed frame saved at: {processed_frame_path}")

            predictions.append({
                "frame": f"/processed_frames/{os.path.basename(frame_path)}",
                "class": waste_class,
                "confidence": confidence_score
            })

        # Compute percentage of bio and non-bio frames
        total_frames = bio_count + non_bio_count
        bio_percentage = (bio_count / total_frames) * 100 if total_frames > 0 else 0
        non_bio_percentage = (non_bio_count / total_frames) * 100 if total_frames > 0 else 0

        # ✅ Send Email **Before Uploading to Google Drive**
        if recipient_email:
            logging.info(f"📧 Sending video classification email in background to {recipient_email}")
            send_video_result_email_smtp_background(
                recipient_email, filename, total_frames, bio_count, non_bio_count
            )

        # ✅ Remove local video file after processing
        if os.path.exists(video_path):
            os.remove(video_path)
            logging.info(f"🗑 Video file {video_path} deleted.")

        # ✅ Start a background thread to upload images to Google Drive
        threading.Thread(target=upload_frames_to_drive, args=(drive_upload_queue,)).start()

        return jsonify({
            "predictions": predictions,
            "bio_percentage": bio_percentage,
            "non_bio_percentage": non_bio_percentage
        })

    except Exception as e:
        logging.error(f"❌ Error processing video: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


def upload_frames_to_drive(frame_queue):
    """
    Asynchronously uploads video frames to Google Drive in the background.
    This ensures that predictions are displayed faster while Drive upload happens separately.
    """
    for frame_path, waste_class in frame_queue:
        try:
            print(f"⏳ Uploading {frame_path} to Google Drive...")
            google_drive_link = upload_to_drive(frame_path, waste_class, is_video_frame=True)
            print(f"✅ Uploaded to Google Drive: {google_drive_link}")
        except Exception as e:
            print(f"❌ Error uploading {frame_path} to Google Drive: {e}")


@app.route("/processed_frames/<filename>")
def get_processed_frame(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, mimetype="image/jpeg")

@app.route("/api/clear_processed_frames", methods=["POST"])
def clear_processed_frames():
    try:
        folder = app.config["PROCESSED_FOLDER"]
        
        # Remove all files from the processed frames folder
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        return jsonify({"message": "All processed frames deleted successfully!"}), 200
    except Exception as e:
        logging.error(f"Error clearing processed frames: {e}")
        return jsonify({"error": "Failed to clear processed frames."}), 500

@app.route("/api/waste_data", methods=["GET"])
def get_waste_data():
    """
    Fetch waste data based on date, time, and type.
    Example Queries:
    - "How much waste was collected on 2025-02-20?"
    - "How much bio-degradable and non-bio-degradable waste was collected today?"
    - "How much waste was collected between 6 PM and 9 PM?"
    """
    date = request.args.get("date")  # Format: YYYY-MM-DD
    start_time = request.args.get("start_time")  # Format: HH:MM (24-hour format)
    end_time = request.args.get("end_time")  # Format: HH:MM (24-hour format)
    waste_type = request.args.get("waste_type")  # "Bio-Degradable" or "Non-Bio-Degradable"

    query = "SELECT waste_type, COUNT(*) FROM records WHERE 1=1"
    params = []

    if date:
        query += " AND DATE(timestamp) = %s"
        params.append(date)
    if start_time and end_time:
        query += " AND TIME(timestamp) BETWEEN %s AND %s"
        params.extend([start_time, end_time])
    if waste_type:
        query += " AND waste_type = %s"
        params.append(waste_type)

    query += " GROUP BY waste_type"

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        conn.close()
        waste_stats = {row["waste_type"]: row["COUNT(*)"] for row in results}
        return jsonify(waste_stats)
    except Exception as e:
        logging.error(f"Error fetching waste data: {e}")
        return jsonify({"error": "An error occurred while retrieving waste data."}), 500


# Helper Functions for API Calls
def fetch_waste_data(params):
    """Fetches waste data based on date, time, or waste type, and returns an HTML response."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/waste_data", params=params)
        data = response.json()

        if "error" in data:
            return f"<p style='color:red;'>❌ <b>Error:</b> {data['error']}</p>"
        if not data:
            return "<p style='color:gray;'>📉 <b>No waste data</b> found for the given period.</p>"

        # Initialize response message
        response_msg = "<div style='font-size: 14px; padding: 10px;'>"
        response_msg += "<p>📊 <b>Waste Collection Data:</b></p>"

        if "date" in params:
            response_msg += f"<p>📅 <b>Date:</b> {params['date']}</p>"
        if "start_time" in params and "end_time" in params:
            response_msg += f"<p>⏰ <b>Time Range:</b> {params['start_time']} - {params['end_time']}</p>"
        if "waste_type" in params:
            response_msg += f"<p>♻ <b>Waste Type:</b> {params['waste_type']}</p>"

        # List waste data
        response_msg += "<ul>"
        for waste_type, count in data.items():
            response_msg += f"<li> <b>{waste_type}:</b> {count} items</li>"
        response_msg += "</ul>"

        response_msg += "</div>"  # Close div
        return response_msg

    except Exception as e:
        return f"<p style='color:red;'>⚠️ <b>Error fetching waste data:</b> {str(e)}</p>"



def fetch_total_waste():
    """Fetches total waste collected count."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/stats")
        data = response.json()
        total_waste = sum(data.values())
        return f"📊 **Total Waste Collected**: {total_waste} items"
    except Exception as e:
        return f"⚠️ Error fetching total waste data: {str(e)}"

def fetch_waste_trend():
    """Fetches waste trends over time."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/trends")
        data = response.json()

        response_msg = "📈 **Waste Collection Trend Over Time:**\n"
        for trend in data:
            response_msg += f"📅 {trend['month']}: {trend['count']} items\n"

        return response_msg
    except Exception as e:
        return f"⚠️ Error fetching waste trend data: {str(e)}"

def fetch_waste_percentage():
    """Fetches bio vs non-bio waste percentage."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/stats")
        data = response.json()

        bio_count = data.get("Bio-Degradable", 0)
        non_bio_count = data.get("Non-Bio-Degradable", 0)
        total_waste = bio_count + non_bio_count

        bio_percentage = (bio_count / total_waste) * 100 if total_waste > 0 else 0
        non_bio_percentage = (non_bio_count / total_waste) * 100 if total_waste > 0 else 0

        return f"📊 **Waste Type Distribution:**\n♻ **Bio-Degradable**: {bio_percentage:.2f}% ({bio_count} items)\n🚯 **Non-Bio-Degradable**: {non_bio_percentage:.2f}% ({non_bio_count} items)"
    except Exception as e:
        return f"⚠️ Error fetching waste percentage data: {str(e)}"

@app.route("/api/waste_by_weekday", methods=["GET"])
def get_waste_by_weekday():
    """
    Fetch waste data for a specific weekday (Monday-Sunday).
    Example Query:
    - "How much waste was collected on Monday?"
    """
    weekday = request.args.get("weekday")  # Expects values like "Monday", "Tuesday", etc.

    if not weekday:
        return jsonify({"error": "Please specify a weekday (e.g., Monday, Tuesday)."}), 400

    # Convert weekday to a number (Monday = 1, Sunday = 7 for MySQL)
    weekday_map = {
        "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
        "Friday": 5, "Saturday": 6, "Sunday": 7
    }

    if weekday not in weekday_map:
        return jsonify({"error": "Invalid weekday provided."}), 400

    weekday_number = weekday_map[weekday]

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT waste_type, COUNT(*) AS count 
                FROM records 
                WHERE DAYOFWEEK(timestamp) = %s 
                GROUP BY waste_type
            ''', (weekday_number,))
            results = cursor.fetchall()

        conn.close()

        if not results:
            return jsonify({"message": f"No waste data found for {weekday}."})

        waste_stats = {row["waste_type"]: row["count"] for row in results}
        return jsonify({
            "date": weekday,
            "waste_data": waste_stats
        })

    except Exception as e:
        logging.error(f"Error fetching waste data for {weekday}: {e}")
        return jsonify({"error": "An error occurred while retrieving waste data."}), 500


def fetch_waste_by_weekday(weekday):
    """Fetches waste data by weekday."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/waste_by_weekday", params={"weekday": weekday})
        data = response.json()

        response_msg = f"🗑 Waste Collection Data for {weekday}:\n"
        for waste_type, count in data["waste_data"].items():
            response_msg += f"🔹 {waste_type}: {count} items\n"

        return response_msg
    except Exception as e:
        return f"⚠️ Error fetching waste data for {weekday}: {str(e)}"

def fetch_monthly_waste_trend(month_year):
    """Fetches waste stats for a specific month and year."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/filter_records", params={"month": month_year})
        data = response.json()

        if "error" in data:
            return f"❌ Error: {data['error']}"
        if not data:
            return f"📉 No waste data found for {month_year}."

        # Count waste types
        bio_count = sum(1 for record in data if record["waste_type"] == "Bio-Degradable")
        non_bio_count = sum(1 for record in data if record["waste_type"] == "Non-Bio-Degradable")
        total_waste = bio_count + non_bio_count

        response_msg = f"📊 Waste Stats for {month_year}:\n"
        response_msg += f"♻ Bio-Degradable: {bio_count} items\n"
        response_msg += f"🚯 Non-Bio-Degradable: {non_bio_count} items\n"
        response_msg += f"🔹 Total Waste: {total_waste} items"

        return response_msg
    except Exception as e:
        return f"⚠️ Error fetching monthly waste data: {str(e)}"


def generate_report_link():
    """Returns a properly formatted clickable report download link using HTML."""
    return "📄 <b>Generating Report...</b> Please wait.<br>✅ <a href='http://127.0.0.1:5000/api/download_report' target='_blank'>Click here to download the report</a>"


# API route to retrieve records
@app.route("/api/records", methods=["GET"])
def get_records():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, filename, waste_type, confidence, timestamp FROM records ORDER BY timestamp DESC')
            records = cursor.fetchall()

        conn.close()

        return jsonify([
            {"id": row["id"], "filename": row["filename"], "waste_type": row["waste_type"],
             "confidence": row["confidence"], "timestamp": row["timestamp"]}
            for row in records
        ])
    except Exception as e:
        logging.error(f"Error retrieving records: {e}")
        return jsonify({"error": "An error occurred while fetching records."}), 500


# API route to get waste statistics
@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Fetches the total count of waste types grouped by category.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT waste_type, COUNT(*) AS count
                FROM records
                GROUP BY waste_type
            ''')
            stats = cursor.fetchall()
        
        conn.close()

        # Convert the data into a dictionary
        result = {row["waste_type"]: row["count"] for row in stats}
        return jsonify(result)

    except Exception as e:
        logging.error(f"Error retrieving waste statistics: {e}")
        return jsonify({"error": "An error occurred while fetching statistics."}), 500

@app.route("/api/trends", methods=["GET"])
def get_trends():
    """
    Fetches monthly waste classification trends.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT DATE_FORMAT(timestamp, '%Y-%m') AS month, COUNT(*) AS count
                FROM records
                GROUP BY month
                ORDER BY month
            ''')
            trends = cursor.fetchall()
        
        conn.close()

        return jsonify([
            {"month": row["month"], "count": row["count"]}
            for row in trends
        ])

    except Exception as e:
        logging.error(f"Error retrieving trends: {e}")
        return jsonify({"error": "An error occurred while fetching trends."}), 500


# API route to get waste distribution (dummy scatter data)
@app.route("/api/distribution", methods=["GET"])
def get_distribution():
    """
    Fetches waste classification confidence scores for visualization.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT id, confidence
                FROM records
            ''')
            distribution = cursor.fetchall()
        
        conn.close()

        return jsonify([
            {"x": row["id"], "y": row["confidence"]} for row in distribution
        ])

    except Exception as e:
        logging.error(f"Error retrieving distribution: {e}")
        return jsonify({"error": "An error occurred while fetching distribution."}), 500


@app.route("/api/filter_records", methods=["GET"])
def filter_records():
    """
    Fetch waste records filtered by date, month, or year.
    """
    date = request.args.get('date')  # Format: 'YYYY-MM-DD'
    month = request.args.get('month')  # Format: 'YYYY-MM'
    year = request.args.get('year')  # Format: 'YYYY'

    query = "SELECT id, filename, waste_type, confidence, timestamp FROM records WHERE 1=1"
    params = []

    if date:
        query += " AND DATE(timestamp) = %s"
        params.append(date)
    if month:
        query += " AND DATE_FORMAT(timestamp, '%Y-%m') = %s"
        params.append(month)
    if year:
        query += " AND YEAR(timestamp) = %s"
        params.append(year)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            records = cursor.fetchall()
        
        conn.close()

        return jsonify([
            {
                "id": row["id"],
                "filename": row["filename"],
                "waste_type": row["waste_type"],
                "confidence": row["confidence"],
                "timestamp": row["timestamp"]
            } for row in records
        ])

    except Exception as e:
        logging.error(f"Error filtering records: {e}")
        return jsonify({"error": "An error occurred while filtering records."}), 500

        
@app.route('/api/download_report', methods=['GET'])
def download_report_with_proper_spacing():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create a centered style for the title
    centered_title_style = ParagraphStyle(
        name="CenteredTitle",
        parent=styles["Title"],
        alignment=TA_CENTER  # Center-align the title
    )

    # Create the title with the new centered style
    title = Paragraph("<b>WMS Report</b>", centered_title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))

    # Calculate bio_count, non_bio_count, and percentages
    cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
    stats = cursor.fetchall()

    bio_count = next((row["count"] for row in stats if row["waste_type"] == "Bio-Degradable"), 0)
    non_bio_count = next((row["count"] for row in stats if row["waste_type"] == "Non-Bio-Degradable"), 0)
    total_count = bio_count + non_bio_count
    bio_percentage = (bio_count / total_count) * 100 if total_count > 0 else 0
    non_bio_percentage = (non_bio_count / total_count) * 100 if total_count > 0 else 0

    # Descriptive Points Section
    descriptions = [
        "1. This report highlights the waste classification between bio-degradable and non-bio-degradable categories.",
        "2. The data is derived from automated waste segregation using machine learning models.",
        "3. Bio-degradable waste includes organic materials such as food waste, paper, and yard waste.",
        "4. Non-bio-degradable waste includes plastics, metals, glass, and other synthetic materials.",
        "5. The pie chart provides a visual representation of the percentage distribution of waste types.",
        "6. The bar chart compares the absolute counts of bio-degradable and non-bio-degradable waste.",
        "7. The waste trend chart shows how waste segregation has varied over months, giving insights into seasonal or operational trends.",
        "8. Confidence scores in the waste distribution chart indicate the reliability of classification predictions.",
        "9. Higher confidence scores signify accurate classifications, while lower scores may need further validation.",
        "10. Understanding the segregation trends helps in planning waste management strategies effectively.",
        "11. Proper waste segregation reduces the impact of waste on the environment and enhances recycling efforts.",
        "12. Bio-degradable waste can be composted to create nutrient-rich fertilizers for agriculture and gardening.",
        "13. Non-bio-degradable waste requires specialized recycling or disposal methods to prevent pollution.",
        "14. Tracking waste trends over time can reveal seasonal patterns and operational inefficiencies.",
        "15. Automated classification helps reduce manual sorting efforts and speeds up waste processing.",
        "16. The reliability of the model is reflected in its confidence scores, ensuring minimal misclassification.",
        "17. Organizations can use this report to identify areas for improving waste management practices.",
        "18. The insights from waste trends can help forecast waste generation and plan resource allocation.",
        "19. A balanced waste segregation system can minimize landfill usage and promote sustainable practices.",
        "20. The visual analytics provided in this report offer a clear and actionable summary for decision-makers."
    ]

    # Modify the paragraph style for justification
    justified_style = styles['Normal']
    justified_style.alignment = TA_JUSTIFY  # Justify alignment

    # Add descriptive points to the PDF
    for desc in descriptions:
        elements.append(Paragraph(desc, justified_style))  # Use justified style
        elements.append(Spacer(1, 10))  # Add spacing between points

    elements.append(PageBreak())  # Add a page break before the charts

    # Pie Chart with Description
    pie_desc = Paragraph("<b>Pie Chart:</b> This chart illustrates the distribution of bio-degradable and non-bio-degradable waste in terms of percentage.", styles['Normal'])
    elements.append(pie_desc)
    elements.append(Spacer(1, 10))

    drawing_pie = Drawing(400, 200)
    pie = Pie()
    pie.x = 150
    pie.y = 50
    pie.data = [bio_count, non_bio_count]
    pie.labels = [f"Bio-Degradable ({bio_percentage:.2f}%)", f"Non-Bio-Degradable ({non_bio_percentage:.2f}%)"]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = Color(0, 0.6, 0)  # Green
    pie.slices[1].fillColor = Color(0.8, 0, 0)  # Red
    drawing_pie.add(pie)
    elements.append(drawing_pie)
    elements.append(Spacer(1, 40))

    # Bar Chart with Description
    bar_desc = Paragraph("<b>Bar Chart:</b> This chart shows the count of bio-degradable and non-bio-degradable wastes.", styles['Normal'])
    elements.append(bar_desc)
    elements.append(Spacer(1, 10))

    drawing_bar = Drawing(400, 200)
    bar_chart = VerticalBarChart()
    bar_chart.x = 50
    bar_chart.y = 50
    bar_chart.height = 150
    bar_chart.width = 300

    # ✅ Ensure both counts are included in the data, even if one is zero
    bar_data = [[bio_count, non_bio_count if non_bio_count > 0 else 0.1]]  # Avoid zero-height bars

    bar_chart.data = bar_data
    bar_chart.categoryAxis.categoryNames = ["Bio-Degradable", "Non-Bio-Degradable"]
    bar_chart.valueAxis.valueMin = 0  # Ensure the y-axis starts at 0
    bar_chart.valueAxis.valueMax = max(bio_count, non_bio_count) + 50  # Set a dynamic max value
    bar_chart.barSpacing = 10  # Add spacing between bars

    # ✅ Prevent zero-height bar issues
    bar_chart.bars[0].fillColor = Color(0, 0.6, 0)  # Green for Bio-Degradable
    bar_chart.bars[1].fillColor = Color(1, 0, 0.2)  # Red for Non-Bio-Degradable

    drawing_bar.add(bar_chart)
    elements.append(drawing_bar)
    elements.append(PageBreak())


    # Waste Trend Chart
    trend_desc = Paragraph("<b>Waste Trend:</b> This line chart shows the trend of waste classification over time.", styles['Normal'])
    elements.append(trend_desc)
    elements.append(Spacer(1, 10))

    cursor.execute("SELECT DATE_FORMAT(timestamp, '%Y-%m') AS month, COUNT(*) FROM records GROUP BY month")
    trend_data = cursor.fetchall()
    months = [row["month"] for row in trend_data]
    counts = [row["COUNT(*)"] for row in trend_data]

    drawing_line = Drawing(400, 200)
    line_chart = HorizontalLineChart()
    line_chart.x = 50
    line_chart.y = 50
    line_chart.data = [counts]
    line_chart.categoryAxis.categoryNames = months
    drawing_line.add(line_chart)
    elements.append(drawing_line)
    elements.append(Spacer(1, 40))

    # Waste Distribution Chart
    distribution_desc = Paragraph("<b>Waste Distribution:</b> This scatter plot shows confidence scores of classified waste.", styles['Normal'])
    elements.append(distribution_desc)
    elements.append(Spacer(1, 10))

    cursor.execute("SELECT id, confidence FROM records ORDER BY timestamp DESC LIMIT 10")
    distribution_data = cursor.fetchall()

    drawing_scatter = Drawing(400, 200)
    scatter_chart = VerticalBarChart()
    scatter_chart.x = 50
    scatter_chart.y = 50
    scatter_chart.data = [[row["confidence"] for row in distribution_data]]
    scatter_chart.categoryAxis.categoryNames = [str(row["id"]) for row in distribution_data]
    scatter_chart.bars[0].fillColor = Color(0.6, 0, 0.8)
    drawing_scatter.add(scatter_chart)
    elements.append(drawing_scatter)
    elements.append(PageBreak())

    # Waste Collection Table
    analytics_title = Paragraph("<b>Waste Collection Data</b>", styles['Title'])
    elements.append(analytics_title)
    elements.append(Spacer(1, 20))

    cursor.execute("SELECT filename, waste_type, confidence, timestamp FROM records")
    records = cursor.fetchall()

    data = [['SI No', 'Filename', 'Type', 'Confidence', 'Timestamp']]
    for index, record in enumerate(records, start=1):
        truncated_filename = record["filename"][:20] + "..." if len(record["filename"]) > 20 else record["filename"]
        data.append([index, truncated_filename, record["waste_type"], f"{record['confidence']:.2f}", record["timestamp"]])

    table = Table(data, colWidths=[50, 200, 100, 80, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)

    # Finalize PDF
    doc.build(elements)
    buffer.seek(0)
    conn.close()
    return send_file(buffer, as_attachment=True, download_name="Report.pdf", mimetype='application/pdf')


@app.route('/api/download_logs', methods=['GET'])
def download_logs():
    try:
        # Fetch log data from the MySQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filename, waste_type, confidence, timestamp FROM records')
        records = cursor.fetchall()
        conn.close()

        # Create CSV content
        def generate():
            data = io.StringIO()
            writer = csv.writer(data)
            # Write header
            writer.writerow(['Filename', 'Type', 'Confidence', 'Timestamp'])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            # Write rows
            for record in records:
                writer.writerow([record["filename"], record["waste_type"], record["confidence"], record["timestamp"]])
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        # Create a streaming response
        return Response(
            generate(),
            mimetype='text/csv',
            headers={
                "Content-Disposition": "attachment; filename=logs.csv"
            }
        )
    except Exception as e:
        logging.error(f"Error generating logs CSV: {e}")
        return jsonify({"error": "An error occurred while generating the CSV file."}), 500


def generate_chart(chart_type, total_waste=None):
    """ Generate different types of charts and return a Matplotlib figure """
    conn = get_db_connection()
    cursor = conn.cursor()

    fig, ax = plt.subplots()

    if chart_type == "pie":
        cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
        stats = cursor.fetchall()
        labels = [row["waste_type"] for row in stats]
        sizes = [row["count"] for row in stats]

        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#4CAF50', '#E74C3C'])
        ax.set_title("Waste Type Distribution")

    elif chart_type == "bar":
        cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
        stats = cursor.fetchall()
        labels = [row["waste_type"] for row in stats]
        counts = [row["count"] for row in stats]

        ax.bar(labels, counts, color=['#4CAF50', '#E74C3C'])
        ax.set_ylabel("Count")
        ax.set_title("Waste Count Comparison")

    elif chart_type == "trend":
        cursor.execute("SELECT DATE_FORMAT(timestamp, '%Y-%m') AS month, COUNT(*) FROM records GROUP BY month")
        stats = cursor.fetchall()
        months = [row["month"] for row in stats]
        counts = [row["COUNT(*)"] for row in stats]

        ax.plot(months, counts, marker='o', linestyle='-', color='#3498DB')
        ax.set_ylabel("Count")
        ax.set_xlabel("Month")
        ax.set_title("Waste Trend Over Time")
        ax.grid(True)

    elif chart_type == "distribution":
        cursor.execute('SELECT id, confidence FROM records ORDER BY timestamp DESC LIMIT 10')
        stats = cursor.fetchall()
        ids = [row["id"] for row in stats]
        confidence = [row["confidence"] for row in stats]

        ax.scatter(ids, confidence, color='#9B59B6', alpha=0.7)
        ax.set_ylabel("Confidence Score")
        ax.set_xlabel("Record ID")
        ax.set_title("Waste Distribution Confidence Scores")
        ax.grid(True)

    elif chart_type == "gauge":
        # Gauge Chart for Waste Processing Efficiency
        min_value = 0
        max_value = 1000  # Assume max waste threshold
        value = total_waste

        # Define colors
        colors = ['#4CAF50', '#F39C12', '#E74C3C']
        zones = [min_value, max_value * 0.5, max_value * 0.8, max_value]

        # Plot background
        for i in range(len(colors)):
            ax.barh(0, zones[i + 1] - zones[i], left=zones[i], color=colors[i], height=0.3)

        # Plot the needle
        ax.scatter(value, 0, color='black', zorder=3, s=150)

        # Labels and limits
        ax.set_xlim(min_value, max_value)
        ax.set_yticks([])
        ax.set_xticks([0, max_value * 0.5, max_value])
        ax.set_xticklabels(['Low', 'Medium', 'High'])

        ax.set_title(f"Total Wastes: {total_waste}")

    conn.close()
    return fig  # Return the Matplotlib figure


def send_email_smtp(recipient_email, subject, html_content, images={}):
    """Send an email with inline images using SMTP."""
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient_email
        msg.set_content("This email contains an HTML body. Please enable HTML viewing.")
        msg.add_alternative(html_content, subtype="html")

        # Attach images using CID
        for img_path, cid in images.items():
            try:
                with open(img_path, "rb") as img_file:
                    img_data = img_file.read()
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if mime_type:
                        maintype, subtype = mime_type.split("/")
                        msg.add_attachment(img_data, maintype=maintype, subtype=subtype, filename=os.path.basename(img_path), cid=cid)
            except Exception as img_error:
                logging.warning(f"⚠️ Warning: Failed to attach image {img_path} - {img_error}")

        # Debug: Log SMTP details
        logging.info(f"📧 Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT} as {EMAIL_SENDER}")

        # Send Email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info(f"✅ Email successfully sent to {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error("❌ Authentication Error: Check your email and password in .env file.")
        return "Authentication Error: Invalid email/password."

    except smtplib.SMTPException as smtp_error:
        logging.error(f"❌ SMTP Exception: {smtp_error}")
        return f"SMTP Error: {smtp_error}"

    except Exception as e:
        logging.error(f"❌ General Email Sending Error: {e}")
        return str(e)


def send_result_email_smtp_background(recipient_email, filename, waste_class, confidence_score):
    """
    Sends waste classification results via email in a background thread.
    """
    def send_email():
        try:
            subject = "Waste Classification Result - Waste Management System"

            # ✅ Define colors inside HTML directly
            if waste_class == "Bio-Degradable":
                class_color = "background-color:#27AE60; color:#FFFFFF; font-weight:bold;"  # Green BG, White Text
            else:
                class_color = "background-color:#E74C3C; color:#FFFFFF; font-weight:bold;"  # Red BG, White Text

            bg_color = "#ECF0F1"  # Light grey background
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")  # Date-Time Format

            html_content = f"""
            <html>
                <head>
                    <style>
                       /* Responsive Email Styles */
                        @media only screen and (max-width: 600px) {{
                            .email-container {{
                                width: 100% !important;
                                padding: 10px !important;
                            }}

                            .email-header {{
                                font-size: 18px !important;
                                padding: 12px !important;
                                text-align: center !important;
                            }}

                            .table-container {{
                                width: 100% !important;
                                display: block !important;
                            }}

                            .table-container tr {{
                                display: flex !important;
                                flex-direction: column !important;
                                align-items: stretch !important;
                                border-bottom: 1px solid #ddd !important;
                                padding: 5px 0 !important;
                            }}

                            .table-container th {{
                                background-color: #2C3E50 !important;
                                color: white !important;
                                text-align: left !important;
                                padding: 10px !important;
                                border-radius: 5px 5px 0 0 !important;
                            }}

                            .table-container td {{
                                background-color: #F4F6F7 !important;
                                padding: 10px !important;
                                border-radius: 0 0 5px 5px !important;
                                text-align: left !important;
                            }}

                            .info-box {{
                                padding: 12px !important;
                                font-size: 13px !important;
                                text-align: justify !important;
                            }}

                            /* Ensure classification row is centered */
                            .classification-row {{
                                text-align: center !important;
                                font-size: 16px !important;
                                font-weight: bold !important;
                            }}
                        }}
                    </style>
                </head>
                <body style="font-family: Arial, sans-serif; background-color: {bg_color}; padding: 20px; margin: 0;">
                    <div class="email-container" style="max-width: 600px; background: white; padding: 25px; border-radius: 10px;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: auto;">

                        <!-- Header -->
                        <div class="email-header" style="background: linear-gradient(90deg, #2C3E50, #34495E); padding: 15px;
                                    border-radius: 8px 8px 0 0; text-align: center;">
                            <h2 style="color: #ECF0F1; margin: 0;">Waste Classification Result</h2>
                        </div>

                        <!-- Classification Details -->
                        <div style="padding: 20px; text-align: left;">
                            <p style="color: #7F8C8D; font-size: 14px;">
                                Below are the details of your recent waste classification.
                            </p>

                            <table class="table-container" style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                                <tr>
                                    <th style="text-align: left; padding: 10px; background-color: #34495E; color: white;">File</th>
                                    <td style="padding: 10px; background-color: #F4F6F7;">{filename}</td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; padding: 10px; background-color: #34495E; color: white;">Classification</th>
                                    <td style="padding: 10px; {class_color} text-align: center;">
                                        {waste_class}
                                    </td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; padding: 10px; background-color: #34495E; color: white;">Confidence Score</th>
                                    <td style="padding: 10px; background-color: #F4F6F7;">{confidence_score:.2f}</td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; padding: 10px; background-color: #34495E; color: white;">Date & Time</th>
                                    <td style="padding: 10px; background-color: #F4F6F7;">{timestamp} (IST)</td>
                                </tr>
                            </table>

                            <!-- Informational Section -->
                            <div class="info-box" style="margin-top: 20px; padding: 15px; background-color: #D5DBDB; border-radius: 6px; text-align: center;">
                                <h4 style="margin: 0; color: #2C3E50;">What This Means?</h4>
                                <p style="font-size: 14px; color: #7F8C8D;">
                                    This result is based on our AI-powered waste classification system. Proper waste segregation
                                    ensures better recycling and environmental sustainability.
                                </p>
                            </div>

                            <!-- Footer -->
                            <div style="margin-top: 20px; text-align: center; font-size: 12px; color: #BDC3C7;">
                                <p>This email was automatically generated by the <b>Waste Management System</b>.</p>
                                <p>Please do not reply to this email.</p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """

            # ✅ Call email function
            email_status = send_email_smtp(recipient_email, subject, html_content)

            if email_status is True:
                logging.info(f"✅ Email sent successfully to {recipient_email}")
            else:
                logging.error(f"❌ Failed to send result email: {email_status}")

        except Exception as e:
            logging.error(f"❌ Error in send_result_email_smtp_background: {e}")

    # ✅ Start email sending in a **background thread**
    email_thread = threading.Thread(target=send_email)
    email_thread.start()


def send_video_result_email_smtp_background(recipient_email, video_filename, total_frames, bio_count, non_bio_count):
    """
    Sends video waste classification results via email in a background thread.
    """
    def send_email():
        try:
            subject = "Video Waste Classification Report - Waste Management System"

            # ✅ Compute Percentages
            bio_percentage = (bio_count / total_frames) * 100 if total_frames > 0 else 0
            non_bio_percentage = (non_bio_count / total_frames) * 100 if total_frames > 0 else 0

            # ✅ Get current Date & Time
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")  # Format: YYYY-MM-DD HH:MM AM/PM

            # ✅ Define Colors
            bio_color = "#27AE60"  # Green
            non_bio_color = "#E74C3C"  # Red
            bg_color = "#ECF0F1"  # Light grey background for contrast

            html_content = f"""
            <html>
                <head>
                    <style>
                        /* General Styles */
                        body {{
                            font-family: 'Arial', sans-serif;
                            background-color: {bg_color};
                            padding: 20px;
                            margin: 0;
                        }}

                        .email-container {{
                            max-width: 650px;
                            background: white;
                            padding: 25px;
                            border-radius: 10px;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                            margin: auto;
                        }}

                        .email-header {{
                            background: linear-gradient(90deg, #2C3E50, #34495E);
                            padding: 15px;
                            border-radius: 8px 8px 0 0;
                            text-align: center;
                        }}

                        .email-header h2 {{
                            color: #ECF0F1;
                            margin: 0;
                        }}

                        .content {{
                            padding: 20px;
                        }}

                        .table-container {{
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 15px;
                        }}

                        .table-container th {{
                            background-color: #BDC3C7;
                            color: white;
                            text-align: left;
                            padding: 10px;
                            border-radius: 5px 5px 0 0;
                        }}

                        .table-container td {{
                            background-color: #F4F6F7;
                            padding: 10px;
                            border-radius: 0 0 5px 5px;
                        }}

                        /* Responsive Styles for Mobile Screens */
                        @media only screen and (max-width: 600px) {{
                            .email-container {{
                                width: 100% !important;
                                padding: 15px !important;
                            }}

                            .email-header h2 {{
                                font-size: 18px !important;
                                padding: 12px !important;
                                text-align: center !important;
                            }}

                            .table-container {{
                                display: block !important;
                            }}

                            .table-container tr {{
                                display: flex !important;
                                flex-direction: column !important;
                                align-items: stretch !important;
                                border-bottom: 1px solid #ddd !important;
                                padding: 5px 0 !important;
                            }}

                            .table-container th {{
                                background-color: #2C3E50 !important;
                                color: white !important;
                                text-align: left !important;
                                padding: 10px !important;
                                border-radius: 5px 5px 0 0 !important;
                            }}

                            .table-container td {{
                                background-color: #F4F6F7 !important;
                                padding: 10px !important;
                                border-radius: 0 0 5px 5px !important;
                                text-align: left !important;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="email-container">

                        <!-- Header -->
                        <div class="email-header">
                            <h2>Video Waste Classification Report</h2>
                        </div>

                        <!-- Classification Details -->
                        <div class="content">
                            <p style="color: #7F8C8D; font-size: 14px;">
                                Below are the results from your recent video waste classification.
                            </p>

                            <table class="table-container">
                                <tr>
                                    <th>Video File</th>
                                    <td>{video_filename}</td>
                                </tr>
                                <tr>
                                    <th>Total Frames Processed</th>
                                    <td>{total_frames}</td>
                                </tr>
                                <tr>
                                    <th>Bio-Degradable</th>
                                    <td style="background-color: {bio_color}; color: white; font-weight: bold;">
                                        {bio_count} frames ({bio_percentage:.2f}%)
                                    </td>
                                </tr>
                                <tr>
                                    <th>Non-Bio-Degradable</th>
                                    <td style="background-color: {non_bio_color}; color: white; font-weight: bold;">
                                        {non_bio_count} frames ({non_bio_percentage:.2f}%)
                                    </td>
                                </tr>
                                <tr>
                                    <th>Date & Time</th>
                                    <td>{timestamp} (IST)</td>
                                </tr>
                            </table>

                            <!-- Informational Section -->
                            <div style="margin-top: 20px; padding: 15px; background-color: #D5DBDB; border-radius: 6px; text-align: center;">
                                <h4>What This Means?</h4>
                                <p style="font-size: 14px; color: #7F8C8D;">
                                    This result is based on our AI-powered waste classification system. Proper waste segregation
                                    ensures better recycling and environmental sustainability.
                                </p>
                            </div>

                            <!-- Footer -->
                            <div style="margin-top: 20px; text-align: center; font-size: 12px; color: #BDC3C7;">
                                <p>This email was automatically generated by the <b>Waste Management System</b>.</p>
                                <p>Please do not reply to this email.</p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """

            # ✅ Call email function
            email_status = send_email_smtp(recipient_email, subject, html_content)

            if email_status is True:
                logging.info(f"✅ Video classification email sent successfully to {recipient_email}")
            else:
                logging.error(f"❌ Failed to send video result email: {email_status}")

        except Exception as e:
            logging.error(f"❌ Error in send_video_result_email_smtp_background: {e}")

    # ✅ Start email sending in a **background thread**
    email_thread = threading.Thread(target=send_email)
    email_thread.start()


@app.route("/api/send_report", methods=["POST"])
def send_report():
    try:
        emails = []
        data = request.form

        # Fetch individual email from request if provided
        recipient_email = data.get("email")
        if recipient_email:
            emails.append(recipient_email)

        # Handle text file upload
        if "file" in request.files:
            file = request.files["file"]
            if file.filename.endswith(".txt"):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                # Read emails from file
                with open(file_path, "r") as f:
                    emails.extend([line.strip() for line in f.readlines() if line.strip()])

        if not emails:
            return jsonify({"error": "No recipient emails found!"}), 400

        # Remove duplicates
        emails = list(set(emails))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch total waste count
        cursor.execute("SELECT COUNT(*) AS total FROM records")
        total_waste = cursor.fetchone()["total"]

        # Fetch waste type counts
        cursor.execute("SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type")
        stats = {row["waste_type"]: row["count"] for row in cursor.fetchall()}

        bio_count = stats.get("Bio-Degradable", 0)
        non_bio_count = stats.get("Non-Bio-Degradable", 0)

        conn.close()

        # Ensure we don't divide by zero
        bio_percentage = (bio_count / total_waste) * 100 if total_waste > 0 else 0
        non_bio_percentage = (non_bio_count / total_waste) * 100 if total_waste > 0 else 0


        # Generate charts
        charts = {
            "pie": "pie_chart.png",
            "bar": "bar_chart.png",
            "trend": "trend_chart.png",
            "distribution": "distribution_chart.png",
        }

        for chart_type, filename in charts.items():
            fig = generate_chart(chart_type)
            fig.savefig(filename, format="png")
            plt.close(fig)  # Free memory

        # Attach images using CID
        images_cid = {filename: filename.split(".")[0] for filename in charts.values()}

        # Email content
        html_content = f"""
        <html>
            <body style="font-family: 'Arial', sans-serif; line-height: 1.6; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 650px; background: white; padding: 25px; border-radius: 10px; 
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: auto;">
                    
                    <!-- Report Title -->
                    <h2 style="color: #2C3E50; text-align: center; margin-bottom: 5px;"> Waste Management System Report</h2>
                    <p style="text-align: center; color: #7F8C8D; font-size: 14px;">
                        Here is the latest report on waste classification, trends, and statistics.
                    </p>

                    <!-- Waste Progress Bars -->
                    <h3 style="color: #27AE60; border-bottom: 2px solid #27AE60; padding-bottom: 5px;">
                        Total Waste Processed
                    </h3>
                    <p style="color: #7F8C8D; font-size: 14px;">
                        This section shows the total waste processed along with the breakdown of <b>Bio-Degradable</b> 
                        and <b>Non-Bio-Degradable</b> waste.
                    </p>
                    <p style="font-size: 14px;"><b>Total Waste:</b> {total_waste} items</p>

                    <!-- Merged Progress Bar -->
                    <div style="background-color: #ecf0f1; width: 100%; border-radius: 10px; overflow: hidden; display: flex;">
                        <div style="width: {bio_percentage:.2f}%; background-color: #27AE60; padding: 5px; 
                                    text-align: center; color: white; font-weight: bold; border-radius: 10px 0 0 10px;">
                            Bio ({bio_count})
                        </div>
                        <div style="width: {non_bio_percentage:.2f}%; background-color: #E74C3C; padding: 5px; 
                                    text-align: center; color: white; font-weight: bold; border-radius: 0 10px 10px 0;">
                            Non-Bio ({non_bio_count})
                        </div>
                    </div>
                    
                    <!-- Waste Type Distribution -->
                    <h3 style="color: #27AE60;">Waste Type Distribution</h3>
                    <p>
                        The pie chart below represents the percentage of waste classified as 
                        <b>Bio-Degradable</b> and <b>Non-Bio-Degradable</b>, helping to understand 
                        the proportion of different waste types.
                    </p>
                    <img src="cid:pie_chart" alt="Pie Chart" width="500" style="border-radius: 8px;">

                    <!-- Waste Count Comparison -->
                    <h3 style="color: #E74C3C;">Waste Count Comparison</h3>
                    <p>
                        This bar chart provides a visual representation of the total waste collected 
                        in each category, showing trends in waste classification.
                    </p>
                    <img src="cid:bar_chart" alt="Bar Chart" width="500" style="border-radius: 8px;">

                    <!-- Waste Trend Over Time -->
                    <h3 style="color: #2980B9;">Waste Trend Over Time</h3>
                    <p>
                        The following line chart shows the trend of waste classification over time, 
                        helping to monitor increases or decreases in waste processing.
                    </p>
                    <img src="cid:trend_chart" alt="Trend Chart" width="500" style="border-radius: 8px;">

                    <!-- Waste Distribution Confidence Scores -->
                    <h3 style="color: #9B59B6;">Waste Distribution Confidence Scores</h3>
                    <p>
                        The scatter plot below shows the confidence scores of the waste classification model, 
                        indicating how accurately the system has been identifying waste types.
                    </p>
                    <img src="cid:distribution_chart" alt="Distribution Chart" width="500" style="border-radius: 8px;">

                    <!-- Footer -->
                    <p style="color: #BDC3C7; text-align: center; font-size: 12px; margin-top: 20px;">
                        This email was generated automatically. Please do not reply.
                    </p>
                </div>
            </body>
        </html>
        """

        # Send email to multiple recipients
        failed_emails = []
        for email in emails:
            email_status = send_email_smtp(email, "Waste Management System Report", html_content, images_cid)
            if email_status is not True:
                failed_emails.append(email)

        if failed_emails:
            return jsonify({"error": f"Failed to send report to: {', '.join(failed_emails)}"}), 500
        return jsonify({"message": "Reports sent successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_chatbot_response(user_query):
    """
    Matches the user query with predefined responses and fetches real-time waste data.
    Converts JSON API responses into human-readable messages using a switch-case dictionary.
    """
    user_query = user_query.lower().strip()

    # Extract date, time, weekday, and waste type from query
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|today|yesterday)\b", user_query)
    time_match = re.search(r"between (\d{1,2} (AM|PM)) and (\d{1,2} (AM|PM))", user_query, re.IGNORECASE)
    weekday_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", user_query, re.IGNORECASE)
    
    # Enhanced regex to support different ways of asking for monthly stats
    month_year_match = re.search(r"(waste stats|waste collected|waste trend) (in|for) (\w+) (\d{4})", user_query)

    waste_type = None
    if "bio waste" in user_query or "bio-degradable" in user_query:
        waste_type = "Bio-Degradable"
    elif "non-bio waste" in user_query or "non-bio-degradable" in user_query:
        waste_type = "Non-Bio-Degradable"

    params = {}
    if date_match:
        date_text = date_match.group(1)
        if date_text.lower() == "today":
            params["date"] = datetime.today().strftime("%Y-%m-%d")
        elif date_text.lower() == "yesterday":
            params["date"] = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            params["date"] = date_text

        # ✅ New code: Fetch actual waste collection data
        try:
            response = requests.get("http://127.0.0.1:5000/api/waste_data", params=params)
            data = response.json()

            if "error" in data:
                return [f"❌ Error: {data['error']}"]
            if not data:
                return [f"📉 No waste data found for {params.get('date', 'the given period')}"]

            # ✅ Format the response correctly
            response_msg = f"📊 Waste Collection Data for {params['date']}:\n"
            for waste_type, count in data.items():
                response_msg += f"🔹 {waste_type}: {count} items\n"

            return [response_msg]
        
        except Exception as e:
            return [f"⚠️ Error fetching waste data: {str(e)}"]  

    if time_match:
        start_hour, start_period = time_match.group(1).split()
        end_hour, end_period = time_match.group(3).split()
        start_hour = int(start_hour) + 12 if start_period.upper() == "PM" and int(start_hour) != 12 else int(start_hour)
        end_hour = int(end_hour) + 12 if end_period.upper() == "PM" and int(end_hour) != 12 else int(end_hour)
        params["start_time"] = f"{start_hour:02d}:00"
        params["end_time"] = f"{end_hour:02d}:00"

    if waste_type:
        params["waste_type"] = waste_type

    
    # Define a switch-case using a dictionary
    switch_case = {
        "waste collected": lambda: fetch_waste_data(params),
        "total waste": fetch_total_waste,
        "waste trend": fetch_waste_trend,
        "bio vs non-bio": fetch_waste_percentage,
        "waste on weekday": lambda: fetch_waste_by_weekday(weekday_match.group(1)) if weekday_match else "❌ Invalid weekday",
        "generate report": generate_report_link
    }

    # Check for specific query types
    for key, action in switch_case.items():
        if key in user_query:
            return [action()]

    # **Handle Monthly Waste Data Queries**
    if month_year_match:
        try:
            month_name, year = month_year_match.group(3), month_year_match.group(4)
            
            if not month_name or not year:
                return ["❌ Invalid query format. Please specify both month and year, e.g., 'Show me waste stats for January 2025'."]

            # Convert month name to numeric format
            month_mapping = {
                "january": "01", "february": "02", "march": "03", "april": "04",
                "may": "05", "june": "06", "july": "07", "august": "08",
                "september": "09", "october": "10", "november": "11", "december": "12"
            }

            month_name_lower = month_name.lower()

            if month_name_lower not in month_mapping:
                return [f"❌ Invalid month: {month_name}. Please enter a valid month (e.g., 'January 2025')."]

            month_numeric = month_mapping[month_name_lower]
            month_year = f"{year}-{month_numeric}"  # Format: YYYY-MM

            return [fetch_monthly_waste_trend(month_year)]
        
        except Exception as e:
            return [f"⚠️ Error processing month-year query: {str(e)}"]



    multiline_keys = {
        "waste_management_best_practices",
        "composting_guide",
        "recycling_tips",
        "government_regulations",
        "ai_model_explanation",
        "report_csv_details",
        "waste_trends_insights",
        "smart_waste_solutions",
        "advanced_troubleshooting",
        "bio_vs_nonbio_detailed",
    }

    # Handle greetings separately (return one random greeting)
    if re.search(r"(?i)\b(hi|hello|hey)\b", user_query):
        return [random.choice(CHATBOT_RESPONSES["hello"])]

    # Check for patterns in user query
    for pattern, key in PATTERN_RESPONSES.items():
        if re.search(pattern, user_query, re.IGNORECASE):
            response_data = CHATBOT_RESPONSES.get(key, ["I'm not sure how to answer that."])

            # ✅ Ensure multiline keys return **all responses as a full concatenated list**
            if key in multiline_keys and isinstance(response_data, list):
                return response_data  # **Returns the full list of responses**

            # ✅ Normal responses return a **single random response**
            elif isinstance(response_data, list):
                return [random.choice(response_data)]

            # ✅ If response is a string, return it wrapped in a list
            else:
                return [response_data]

    # **🔹 Default Response**
    return ["🤖 I'm not sure how to answer that. Please try rephrasing your question or ask something else about waste management."]


@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_query = data.get("query")

    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    response_list = get_chatbot_response(user_query)
    response_text = "\n\n".join(response_list)
    response = response_list[0]  # Pick the first response

    return jsonify({"response": response})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.template_folder, "index.html")

@app.route("/")
def home():
    return "WMS is Working Properly"

if __name__ == '__main__':
    print("\n🚀 Flask is starting...") 
    print("\n Now, You are good to go ✅") # Explicit startup message
    app.run()
