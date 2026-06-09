from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
from config import Config
from models import User
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import cv2
import numpy as np
from ultralytics import YOLO
import torch
from twilio.rest import Client

app = Flask(__name__)
app.config.from_object(Config)

# Load YOLO models (using available models; prioritize newer versions for better accuracy)
try:
    yolo_v11 = YOLO('yolov11n.pt')  # Latest YOLOv11 for better detection
except:
    yolo_v11 = None
try:
    yolo_v9 = YOLO('yolov9c.pt')  # Fallback to YOLOv9
except:
    yolo_v9 = None
try:
    yolo_v8 = YOLO('yolov8n.pt')  # Fallback to YOLOv8
except:
    yolo_v8 = None

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def send_alert_email(subject, body, image_path=None, location=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = ', '.join([Config.ADMIN_EMAIL] + Config.EMERGENCY_EMAILS)
        msg['Subject'] = subject

        body += f"\nLocation: {location}" if location else ""
        msg.attach(MIMEText(body, 'plain'))

        if image_path:
            with open(image_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                msg.attach(img)

        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(Config.MAIL_USERNAME, [Config.ADMIN_EMAIL] + Config.EMERGENCY_EMAILS, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_alert_sms(body, location=None):
    try:
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        message_body = body
        if location:
            message_body += f"\nLocation: {location}"
        for number in Config.EMERGENCY_PHONE_NUMBERS:
            client.messages.create(
                body=message_body,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=number
            )
        return True
    except Exception as e:
        print(f"SMS sending failed: {e}")
        return False

def detect_accident(image_path):
    # Prioritize YOLOv11, then v9, then v8
    model = yolo_v11 or yolo_v9 or yolo_v8
    if model is None:
        print("No YOLO model loaded")
        return False, image_path  # Return original if no model

    try:
        # Check if it's a video file
        if image_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            cap = cv2.VideoCapture(image_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                cap.release()
                print("Video has no frames")
                return False, image_path

            # Sample up to 50 frames evenly distributed for better detection
            num_samples = min(50, total_frames)
            frame_indices = [int(i * (total_frames - 1) / (num_samples - 1)) for i in range(num_samples)] if num_samples > 1 else [0]

            accident_detected = False
            result_img = None
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, img = cap.read()
                if not ret or img is None:
                    continue

                results = model(img)
                car_count = 0
                person_count = 0
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = box.conf[0]
                        if conf < 0.3:  # Lower confidence threshold for better detection
                            continue
                        if cls == 2:  # Car class
                            car_count += 1
                            x1, y1, x2, y2 = box.xyxy[0]
                            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                            cv2.putText(img, 'Car', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
                        elif cls == 0:  # Person class
                            person_count += 1
                            x1, y1, x2, y2 = box.xyxy[0]
                            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                            cv2.putText(img, 'Person', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,0), 2)

                # Adjusted logic: Accident if multiple cars or cars with people (potential accident scene)
                # More sensitive: more than 2 cars or 1+ cars with 1+ people
                print(f"Frame {idx}: Detected {car_count} cars, {person_count} persons")
                if car_count > 2 or (car_count >= 1 and person_count >= 1):
                    accident_detected = True
                    cv2.putText(img, 'Potential Accident', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    result_img = img  # Use the frame where accident is detected
                    break  # Stop at first accident detection

            cap.release()
            if not accident_detected:
                # If no accident, use the last sampled frame for result image
                if result_img is None:
                    cap = cv2.VideoCapture(image_path)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_indices[-1])
                    ret, result_img = cap.read()
                    cap.release()
                    if not ret or result_img is None:
                        return False, image_path
            img = result_img
        else:
            img = cv2.imread(image_path)
    except Exception as e:
        print(f"Error reading image/video: {e}")
        return False, image_path

    if img is None or img.size == 0:
        print("Failed to read image or image is empty")
        return False, image_path

    # For images, run detection if not already done
    if not image_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        results = model(img)  # Use the best available model
        car_count = 0
        person_count = 0
        accident_detected = False
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = box.conf[0]
                if conf < 0.3:  # Lower confidence threshold for better detection
                    continue
                if cls == 2:  # Car class
                    car_count += 1
                    x1, y1, x2, y2 = box.xyxy[0]
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                    cv2.putText(img, 'Car', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
                elif cls == 0:  # Person class
                    person_count += 1
                    x1, y1, x2, y2 = box.xyxy[0]
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(img, 'Person', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,0), 2)

        # Adjusted logic: Accident if multiple cars or cars with people (potential accident scene)
        # More sensitive: more than 2 cars or 1+ cars with 1+ people
        print(f"Detected: {car_count} cars, {person_count} persons")
        if car_count > 2 or (car_count >= 1 and person_count >= 1):
            accident_detected = True
            cv2.putText(img, 'Potential Accident', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        print(f"Accident detected: {accident_detected}")

    result_path = os.path.join(RESULT_FOLDER, 'result_' + os.path.basename(image_path).rsplit('.', 1)[0] + '.jpg')
    cv2.imwrite(result_path, img)
    return accident_detected, result_path

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('upload'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_by_username(username)
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('upload'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.get_by_username(username):
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('register'))
        User.create(username, email, password)
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['file']
        location = request.form.get('location', 'Unknown')
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            accident, result_path = detect_accident(filepath)
            if accident:
                email_sent = send_alert_email('Accident Detected', 'An accident has been detected in the uploaded image.', result_path, location)
                sms_sent = send_alert_sms('Accident Detected: An accident has been detected in the uploaded image.', location)
                if email_sent or sms_sent:
                    flash('Accident detected! Alert sent.')
                else:
                    flash('Accident detected! Alert failed to send.')
            else:
                flash('No accident detected.')
            return render_template('result.html', result_image=os.path.basename(result_path), accident=accident)
    return render_template('upload.html')

@app.route('/detect_live', methods=['POST'])
def detect_live():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    file = request.files['file']
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Simplified live detection: just count objects without saving annotated image
    model = yolo_v11 or yolo_v9 or yolo_v8
    if model is None:
        return jsonify({'error': 'No model loaded'}), 500

    try:
        img = cv2.imread(filepath)
        if img is None or img.size == 0:
            return jsonify({'error': 'Invalid image'}), 400

        results = model(img)
        car_count = 0
        person_count = 0
        accident_detected = False

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = box.conf[0]
                if conf < 0.3:  # Lower threshold for live detection
                    continue
                if cls == 2:  # Car
                    car_count += 1
                elif cls == 0:  # Person
                    person_count += 1

        # Accident logic for live detection - more sensitive
        if car_count > 2 or (car_count >= 1 and person_count >= 1):
            accident_detected = True

        return jsonify({
            'cars': car_count,
            'persons': person_count,
            'accident': accident_detected
        })
    except Exception as e:
        print(f"Live detection error: {e}")
        return jsonify({'error': 'Detection failed'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
