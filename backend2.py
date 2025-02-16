from flask import Flask, request, jsonify
from keras.models import load_model
from keras.layers import DepthwiseConv2D
from PIL import Image, ImageOps
import numpy as np
import os
import cv2
import sqlite3
from datetime import datetime
from flask_cors import CORS
import logging
from flask import send_from_directory
from flask import Response
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
import csv
import io
import smtplib
import os
import mimetypes
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') 
from email.message import EmailMessage
from flask import Flask, send_from_directory, render_template
from werkzeug.utils import secure_filename
from flask import request, jsonify, send_file
import base64

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

SMTP_SERVER = "smtp.gmail.com"  # Change for Outlook, Yahoo, etc.
SMTP_PORT = 587
EMAIL_SENDER = "wastemgmtsys@gmail.com"
EMAIL_PASSWORD = "fnbm vusr rsxe sksu"  # Use App Password if necessary



# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize SQLite Database
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                waste_type TEXT,
                confidence REAL,
                timestamp TEXT
            )
        ''')
        conn.commit()

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


# Function to save prediction results in SQLite
def save_record(filename, waste_type, confidence):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO records (filename, waste_type, confidence, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (filename, waste_type, confidence, timestamp))
    conn.commit()
    conn.close()

@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        if "file" not in request.files:
            logging.error("No file uploaded in request.")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            logging.error("No file selected for upload.")
            return jsonify({"error": "No file selected"}), 400

        logging.info(f"File received: {file.filename}")

        # Generate unique filename to avoid conflicts
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        temp_file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Save the file temporarily
        file.save(temp_file_path)
        logging.info(f"File saved temporarily at: {temp_file_path}")

        # Predict waste type
        result = predict_image(temp_file_path)
        logging.info(f"Prediction result: {result}")

        if "bio" in result and "nonBio" in result:
            waste_class = "Bio-Degradable" if result["bio"] > result["nonBio"] else "Non-Bio-Degradable"
            confidence_score = max(result["bio"], result["nonBio"])

            # Save the result in the database
            save_record(filename, waste_class, confidence_score)

            response_data = {
                "class": waste_class,
                "bio": result["bio"],
                "nonBio": result["nonBio"],
                "confidence_score": confidence_score
            }

            logging.info(f"Prediction saved to database: {response_data}")

        else:
            logging.error("Invalid prediction response format.")
            return jsonify({"error": "Prediction failed. Invalid response format."}), 500

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return jsonify({"error": "An error occurred during processing."}), 500

    finally:
        # Ensure cleanup of temporary file even in case of exceptions
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logging.info(f"Temporary file {temp_file_path} deleted.")

    return jsonify(response_data)

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
    if "file" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save uploaded video
    video_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(video_path)
    print(f"📂 Video saved at: {video_path}")

    # Extract frames
    frames_folder = os.path.join(app.config["UPLOAD_FOLDER"], "frames")
    os.makedirs(frames_folder, exist_ok=True)
    frame_files = extract_frames(video_path, frames_folder, frame_interval=30)

    if not frame_files:
        print("⚠️ No frames extracted!")
        return jsonify({"error": "Failed to extract frames from video"}), 500

    predictions = []
    bio_count = 0
    non_bio_count = 0

    for frame_path in frame_files:
        print(f"🖼 Processing frame: {frame_path}")
        result = predict_image(frame_path)

        if "error" in result:
            print(f"⚠️ Prediction failed for {frame_path}")
            continue

        waste_class = "Bio-Degradable" if result["bio"] > result["nonBio"] else "Non-Bio-Degradable"
        confidence_score = max(result["bio"], result["nonBio"])

        # Count classification types
        if waste_class == "Bio-Degradable":
            bio_count += 1
        else:
            non_bio_count += 1

        # Save prediction to the database
        save_record(os.path.basename(frame_path), waste_class, confidence_score)

        # Load the frame for drawing
        frame = cv2.imread(frame_path)
        if frame is None:
            print(f"⚠️ Failed to read image {frame_path}")
            continue

        # Draw Prediction on Frame
        label = f"{waste_class} ({confidence_score:.2f})"
        color = (0, 255, 0) if waste_class == "Bio-Degradable" else (0, 0, 255)
        cv2.putText(frame, label, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        # Save Processed Frame
        processed_frame_path = os.path.join(PROCESSED_FOLDER, os.path.basename(frame_path))
        cv2.imwrite(processed_frame_path, frame)
        print(f"✅ Processed frame saved at: {processed_frame_path}")

        predictions.append({
            "frame": f"/processed_frames/{os.path.basename(frame_path)}",
            "class": waste_class,
            "confidence": confidence_score
        })

    # Compute percentage of bio and non-bio frames
    total_frames = bio_count + non_bio_count
    bio_percentage = (bio_count / total_frames) * 100 if total_frames > 0 else 0
    non_bio_percentage = (non_bio_count / total_frames) * 100 if total_frames > 0 else 0

    # Cleanup: Remove video
    os.remove(video_path)

    return jsonify({
        "predictions": predictions,
        "bio_percentage": bio_percentage,
        "non_bio_percentage": non_bio_percentage
    })


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

# API route to retrieve records
@app.route("/api/records", methods=["GET"])
def get_records():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, filename, waste_type, confidence, timestamp FROM records ORDER BY timestamp DESC')
            records = cursor.fetchall()
        return jsonify([
            {"id": row[0], "filename": row[1], "waste_type": row[2], "confidence": row[3], "timestamp": row[4]}
            for row in records
        ])
    except Exception as e:
        logging.error(f"Error retrieving records: {e}")
        return jsonify({"error": "An error occurred while fetching records."}), 500

# API route to get waste statistics
@app.route("/api/stats", methods=["GET"])
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT waste_type, COUNT(*) as count
        FROM records
        GROUP BY waste_type
    ''')
    stats = cursor.fetchall()
    conn.close()

    # Convert the data into a dictionary
    result = {row[0]: row[1] for row in stats}
    return jsonify(result)

# API route to get waste trends (e.g., monthly counts)
@app.route("/api/trends", methods=["GET"])
def get_trends():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as count
                FROM records
                GROUP BY month
                ORDER BY month
            ''')
            trends = cursor.fetchall()
        return jsonify([
            {"month": row[0], "count": row[1]}
            for row in trends
        ])
    except Exception as e:
        logging.error(f"Error retrieving trends: {e}")
        return jsonify({"error": "An error occurred while fetching trends."}), 500

# API route to get waste distribution (dummy scatter data)
@app.route("/api/distribution", methods=["GET"])
def get_distribution():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT confidence, id
                FROM records
            ''')
            distribution = cursor.fetchall()
        return jsonify([
            {"x": row[1], "y": row[0]} for row in distribution
        ])
    except Exception as e:
        logging.error(f"Error retrieving distribution: {e}")
        return jsonify({"error": "An error occurred while fetching distribution."}), 500

@app.route("/api/filter_records", methods=["GET"])
def filter_records():
    date = request.args.get('date')  # Format: 'YYYY-MM-DD'
    month = request.args.get('month')  # Format: 'YYYY-MM'
    year = request.args.get('year')  # Format: 'YYYY'
    
    query = "SELECT id, filename, waste_type, confidence, timestamp FROM records WHERE 1=1"
    params = []
    
    if date:
        query += " AND DATE(timestamp) = ?"
        params.append(date)
    if month:
        query += " AND strftime('%Y-%m', timestamp) = ?"
        params.append(month)
    if year:
        query += " AND strftime('%Y', timestamp) = ?"
        params.append(year)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            records = cursor.fetchall()
        return jsonify([{
            "id": row[0], "filename": row[1], "waste_type": row[2], "confidence": row[3], "timestamp": row[4]
        } for row in records])
    except Exception as e:
        logging.error(f"Error filtering records: {e}")
        return jsonify({"error": "An error occurred while filtering records."}), 500

        
@app.route('/api/download_report', methods=['GET'])
def download_report_with_proper_spacing():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title Section
    title = Paragraph("<b>Waste Management System</b>", styles['Title'])
    subtitle_style = styles['Normal']
    subtitle_style.alignment = TA_CENTER  # Center align the subtitle
    subtitle = Paragraph(
        f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        subtitle_style
    )
    elements.append(title)
    elements.append(subtitle)
    elements.append(Spacer(1, 20))

    # Fetch data from the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT filename, waste_type, confidence, timestamp FROM records')
    records = cursor.fetchall()

    # Table Headers and Data
    data = [['Filename', 'Type', 'Confidence', 'Timestamp']]  # Header row
    for record in records:
        truncated_filename = record[0][:10] + "..." if len(record[0]) > 20 else record[0]
        data.append([truncated_filename, record[1], f"{record[2]:.2f}", record[3]])

    # Create Table
    table = Table(data, colWidths=[200, 100, 80, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(PageBreak())  # Add a page break before analytics

    # Analytics Section
    analytics_title = Paragraph("<b>Analytics and Insights</b>", styles['Title'])
    elements.append(analytics_title)
    elements.append(Spacer(1, 20))

    # Calculate bio_count, non_bio_count, and percentages
    cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
    stats = cursor.fetchall()

    bio_count = next((row[1] for row in stats if row[0] == "Bio-Degradable"), 0)
    non_bio_count = next((row[1] for row in stats if row[0] == "Non-Bio-Degradable"), 0)
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
    pie_desc = Paragraph(
        "<b>Pie Chart:</b> This chart illustrates the distribution of bio-degradable and non-bio-degradable waste in terms of percentage.",
        styles['Normal']
    )
    elements.append(pie_desc)
    elements.append(Spacer(1, 10))
    drawing_pie = Drawing(400, 200)
    pie = Pie()
    pie.x = 150
    pie.y = 50
    pie.data = [bio_count, non_bio_count]
    pie.labels = [
        f"Bio-Degradable ({bio_percentage:.2f}%)",
        f"Non-Bio-Degradable ({non_bio_percentage:.2f}%)"
    ]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = Color(0, 0.6, 0)  # Green for Bio-Degradable
    pie.slices[1].fillColor = Color(0.8, 0, 0)  # Red for Non-Bio-Degradable
    drawing_pie.add(pie)
    elements.append(drawing_pie)
    elements.append(Spacer(1, 40))

    # Bar Chart with Description
    bar_desc = Paragraph(
        "<b>Bar Chart:</b> This chart shows the count of bio-degradable and non-bio-degradable wastes.",
        styles['Normal']
    )
    elements.append(bar_desc)
    elements.append(Spacer(1, 10))

    # Ensure both counts are included in the data, even if one is zero
    bar_data = [[bio_count, non_bio_count]]

    drawing_bar = Drawing(400, 200)
    bar_chart = VerticalBarChart()
    bar_chart.x = 50
    bar_chart.y = 50
    bar_chart.height = 150
    bar_chart.width = 300
    bar_chart.data = bar_data
    bar_chart.categoryAxis.categoryNames = ["Bio-Degradable", "Non-Bio-Degradable"]
    bar_chart.valueAxis.valueMin = 0
    bar_chart.valueAxis.valueMax = max(bar_data[0]) + 2  # Adjust the maximum value
    bar_chart.bars[0].fillColor = Color(0, 0.6, 0)  # Green for Bio-Degradable
    bar_chart.bars[1].fillColor = Color(1, 0, 0.2)  # Red for Non-Bio-Degradable

    drawing_bar.add(bar_chart)
    elements.append(drawing_bar)
    elements.append(PageBreak())


    # Waste Trend (Line Chart) with Description
    trend_desc = Paragraph(
        "<b>Waste Trend:</b> This line chart shows the trend of waste classification over time, grouped by months.",
        styles['Normal']
    )
    elements.append(trend_desc)
    elements.append(Spacer(1, 10))
    cursor.execute('SELECT strftime("%Y-%m", timestamp) AS month, COUNT(*) FROM records GROUP BY month')
    trend_data = cursor.fetchall()
    months = [row[0] for row in trend_data]
    counts = [row[1] for row in trend_data]

    drawing_line = Drawing(400, 200)
    line_chart = HorizontalLineChart()
    line_chart.x = 50
    line_chart.y = 50
    line_chart.height = 150
    line_chart.width = 300
    line_chart.data = [counts]
    line_chart.categoryAxis.categoryNames = months
    line_chart.categoryAxis.labels.angle = 45
    line_chart.categoryAxis.labels.boxAnchor = 'n'
    line_chart.valueAxis.valueMin = 0
    line_chart.valueAxis.valueMax = max(counts) + 2
    line_chart.lines[0].strokeWidth = 2
    drawing_line.add(line_chart)
    elements.append(drawing_line)
    elements.append(Spacer(1, 40))

    # Waste Distribution (Scatter Plot) with Description
    distribution_desc = Paragraph(
        "<b>Waste Distribution:</b> This scatter plot shows the confidence scores of the last 10 classified wastes.",
        styles['Normal']
    )
    elements.append(distribution_desc)
    elements.append(Spacer(1, 10))

    # Fetch data from the database
    cursor.execute('SELECT id, confidence FROM records')
    distribution_data = cursor.fetchall()

    # Extract only the last 10 records
    last_10_distributions = distribution_data[-10:]

    # Create the scatter plot
    drawing_scatter = Drawing(400, 200)
    scatter_chart = VerticalBarChart()  # Bar-like scatter for simplicity
    scatter_chart.x = 50
    scatter_chart.y = 50
    scatter_chart.height = 150
    scatter_chart.width = 300
    scatter_chart.data = [[row[1] for row in last_10_distributions]]
    scatter_chart.categoryAxis.categoryNames = [str(row[0]) for row in last_10_distributions]
    scatter_chart.bars[0].fillColor = Color(0.6, 0, 0.8)

    # Add the chart to the drawing and append it to the elements
    drawing_scatter.add(scatter_chart)
    elements.append(drawing_scatter)

    # Finalize PDF
    doc.build(elements)
    buffer.seek(0)
    conn.close()
    return send_file(buffer, as_attachment=True, download_name="Report.pdf", mimetype='application/pdf')

@app.route('/api/download_logs', methods=['GET'])
def download_logs():
    try:
        # Fetch log data from the database
        conn = sqlite3.connect(DB_PATH)
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
                writer.writerow(record)
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    fig, ax = plt.subplots()

    if chart_type == "pie":
        cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
        stats = cursor.fetchall()
        labels = [row[0] for row in stats]
        sizes = [row[1] for row in stats]

        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#4CAF50', '#E74C3C'])
        ax.set_title("Waste Type Distribution")

    elif chart_type == "bar":
        cursor.execute('SELECT waste_type, COUNT(*) as count FROM records GROUP BY waste_type')
        stats = cursor.fetchall()
        labels = [row[0] for row in stats]
        counts = [row[1] for row in stats]

        ax.bar(labels, counts, color=['#4CAF50', '#E74C3C'])
        ax.set_ylabel("Count")
        ax.set_title("Waste Count Comparison")

    elif chart_type == "trend":
        cursor.execute('SELECT strftime("%Y-%m", timestamp) AS month, COUNT(*) FROM records GROUP BY month')
        stats = cursor.fetchall()
        months = [row[0] for row in stats]
        counts = [row[1] for row in stats]

        ax.plot(months, counts, marker='o', linestyle='-', color='#3498DB')
        ax.set_ylabel("Count")
        ax.set_xlabel("Month")
        ax.set_title("Waste Trend Over Time")
        ax.grid(True)

    elif chart_type == "distribution":
        cursor.execute('SELECT id, confidence FROM records')
        stats = cursor.fetchall()
        ids = [row[0] for row in stats[-10:]]  # Last 10 records
        confidence = [row[1] for row in stats[-10:]]

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


def send_email_smtp(recipient_email, subject, html_content, images):
    """ Send an email with inline images using CID """
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient_email
        msg.set_content("This email contains an HTML body. Please enable HTML viewing.")
        msg.add_alternative(html_content, subtype="html")

        # Attach images using CID
        for img_path, cid in images.items():
            with open(img_path, "rb") as img_file:
                img_data = img_file.read()
                maintype, subtype = mimetypes.guess_type(img_path)[0].split("/")
                msg.add_attachment(img_data, maintype=maintype, subtype=subtype, cid=cid)

        # Send Email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        return str(e)


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

        # Fetch waste statistics
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM records")
        total_waste = cursor.fetchone()[0]

        cursor.execute("SELECT waste_type, COUNT(*) FROM records GROUP BY waste_type")
        stats = dict(cursor.fetchall())

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

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.template_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True)
