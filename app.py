# Required Imports
import os
from flask import Flask, request, jsonify, render_template, Response, jsonify, request, redirect, url_for
from firebase_admin import credentials, firestore, initialize_app
import cv2
import vcount
import threading
import signal
import schedule
import atexit
import datetime
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
from itsdangerous import URLSafeTimedSerializer
import requests
import smtplib
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'admin'

mysql = MySQL(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# Initialize Firestore DB
cred = credentials.Certificate('vcount-sst3-firebase-adminsdk-vc9pj-77b3634bae.json')
default_app = initialize_app(cred)
db = firestore.client()

cap = None
cap1 = cv2.VideoCapture(0)  # Variabel untuk webcam
cap2 = cv2.VideoCapture('videos/vidp.mp4')  # Variabel untuk video lokal

# Variabel global untuk menyimpan respon terakhir
last_response = None

# Fungsi untuk menghentikan aliran video
def stop_video_feed():
    global cap
    if cap is not None:
        cap.release()
        cap = None

# Fungsi untuk menghasilkan OTP acak
def generate_otp():
    otp = random.randint(100000, 999999)
    return otp

# Fungsi untuk memeriksa OTP yang dimasukkan pengguna
def check_otp(saved_otp, entered_otp):
    return saved_otp == int(entered_otp)

# Fungsi untuk mengirim OTP melalui metode yang sesuai (email)
def send_otp(username, otp):
    # Pengaturan server email
    smtp_server = 'smtp.gmail.com'
    port = 587  # Port SMTP server
    sender_email = 'firsteam57@gmail.com'
    sender_password = 'qvcjxwiqcwysiqwk'

    # Menyiapkan pesan email
    subject = 'One-Time Password (OTP) Verification'
    message = f'Hello {username},\n\nOTP kamu: {otp}\n\nVerifikasikan akun anda dengan OTP tersebut'
    email_body = f'Subject: {subject}\n\n{message}'

    try:
        # Mengirim email
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [username], email_body)
        print('OTP sent successfully')
    except Exception as e:
        print('Failed to send OTP:', str(e))
    pass

# Route untuk halaman utama
@app.route('/')
def main():
    return render_template('login.html')

# Route untuk register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        otp = generate_otp()

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users(username, password, otp) VALUES(%s, %s, %s)", (username, password, otp))
        mysql.connection.commit()
        cursor.close()

        send_otp(username, otp)  # Fungsi untuk mengirim OTP

        return redirect(url_for('verify_otp', username=username))
    return render_template('register.html')


# Route untuk verifikasi OTP
@app.route('/verify-otp/<username>', methods=['GET', 'POST'])
def verify_otp(username):
    if request.method == 'POST':
        otp_entered = request.form['otp']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT otp FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result and check_otp(result[0], otp_entered):
            cursor.execute("UPDATE users SET verified = 1 WHERE username = %s", (username,))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('login'))
        cursor.close()
        return render_template('verify_otp.html', username=username, message='Invalid OTP')
    return render_template('verify_otp.html', username=username)


# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT password, verified FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()

        if result and bcrypt.check_password_hash(result[0], password):
            if result[1] == 1:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('verify_otp', username=username))
        cursor.close()
        return render_template('login.html', message='Invalid username or password')
    return render_template('login.html')

# Route untuk edit data pengguna
@app.route('/edit-user', methods=['POST'])
def edit_user():
    user_id = request.form['user_id']
    username = request.form['username']
    password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET username = %s, password = %s WHERE id = %s",
                   (username, password, user_id))
    mysql.connection.commit()
    cursor.close()
    return "User updated successfully"

# Route untuk menghapus data pengguna
@app.route('/delete-user', methods=['DELETE'])
def delete_user():
    user_id = request.form['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cursor.close()

    return "User deleted successfully"

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Rute untuk mengirimkan aliran video.
@app.route('/video_feed')
def video_feed():
    return Response(vcount.v_count(cap), mimetype='multipart/x-mixed-replace; boundary=frame')

# Route untuk logout
@app.route('/logout')
def logout():
    stop_video_feed()  # Menghentikan aliran video
    return redirect(url_for('main'))  # Kembali ke halaman login



# Rute untuk mengatur sumber video yang akan digunakan.
@app.route('/set_video_feed', methods=['POST'])
def set_video_feed():
    global cap
    video_path = request.form.get('video_path')
    if video_path == '0':
        if cap is not None:
            cap.release()
        cap = cap1
    elif video_path == '1':
        if cap is not None:
            cap.release()
        cap = cap2
    elif video_path == '2':
        if cap is not None:
            cap.release()
        cap = cv2.VideoCapture('http://192.168.108.63:4747/video')  # Variabel untuk IP camera
    return redirect(url_for('dashboard'))

# ngambil table collection di firestore dengan nama "counting"
todo_ref = db.collection('counting')

# Menangkap sinyal penutupan
@atexit.register
def on_exit():
    send_last_response()

# Rute untuk mendapatkan data hitung jumlah orang.
@app.route('/counter', methods=['GET'])
def counter():
    down, up, total = vcount.get_counter()

    # Periksa apakah ada data dengan tanggal hari ini
    date_today = datetime.datetime.now().date()
    date_string = str(date_today)  # Ubah tanggal menjadi string
    query = todo_ref.where('dateString', '==', date_string).limit(1).get()

    if len(query) > 0:
        # Jika ada, perbarui data
        id = query[0].id
        todo_ref.document(id).update({
            'total_masuk': down,
            'total_keluar': up,
            'total_pengunjung': total
        })
    else:
        # Jika tidak ada, simpan data respon terakhir
        response = {
            'total_masuk': down,
            'total_keluar': up,
            'total_pengunjung': total,
            'date': datetime.datetime.now(),
            'dateString': date_string
        }
        global last_response
        last_response = response

    return jsonify(last_response)

# Fungsi untuk mengirim data ke '/add'
def send_last_response():
    if last_response is not None:
        with app.test_client() as client:
            client.post('http://127.0.0.1:8000/add', json=last_response)

#nambah data counting
@app.route('/add', methods=['POST'])
def create():
    try:
        totalMasuk = request.json['total_masuk']
        totalKeluar = request.json['total_keluar']
        totalPengunjung = request.json['total_pengunjung']
        dateString = str(datetime.datetime.now())[:10]
        ct = datetime.datetime.now()
        todo_ref.add(
            {
                "total_masuk": totalMasuk,
                "total_keluar": totalKeluar,
                "total_pengunjung": totalPengunjung,
                "date": ct,
                "dateString": dateString
            }
        )
        # todo_ref.document(id).set(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"


#get data counting  
@app.route('/list', methods=['GET'])
def read():
    try:
        # Check if ID was passed to URL query
        todo_id = request.args.get('id')    
        if todo_id:
            todo = todo_ref.document(todo_id).get()
            return jsonify(todo.to_dict()), 200
        else:
            all_todos = [doc.to_dict() for doc in todo_ref.stream()]
            return jsonify(all_todos), 200
    except Exception as e:
        return f"An Error Occured: {e}"

#get data pie chart    
@app.route('/pie-chart', methods=['GET'])
def pieCart():
    try:
        dateSNow = str(datetime.datetime.now())[:10]
        query = todo_ref.where('dateString', '==', dateSNow)
        result = query.get()
        response = {}
        if len(result) > 0:
            for doc in result:
                response = doc.to_dict()
    
            jumlah_pengunjung = response['total_masuk'] - response['total_keluar']
            jumlah_maksimal = jumlah_pengunjung / 200
            jumlah_persen = jumlah_maksimal * 100
            response = {
                'name': 'total_persen',
                'total': jumlah_persen,
                'total_pengunjung': jumlah_pengunjung
            }
        else :
             response = {
                'name': 'total_persen',
                'total': 0.0,
                'total_pengunjung': 0
            }
             
        return jsonify(response),200
    except Exception as e:
        return f"An Error Occured: {e}"

#get data bar chart
@app.route('/bar-chart', methods=['GET'])
def barChart():
    try:
        all_todos = [doc.to_dict() for doc in todo_ref.stream()]
        return jsonify(all_todos),
    except Exception as e:
        return f"An Error Occured: {e}"

#update data counting    
@app.route('/update', methods=['POST', 'PUT'])
def update():
    try:
        id = request.json['id']
        todo_ref.document(id).update(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"

#delete data counting   
@app.route('/delete', methods=['GET', 'DELETE'])
def delete():
    try:
        # Check for ID in URL query
        todo_id = request.args.get('id')
        todo_ref.document(todo_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"

if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=8000)
