from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS messages')
    c.execute('DROP TABLE IF EXISTS chats')
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')
    c.execute('''
    CREATE TABLE chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        chat_name TEXT NOT NULL
    )
    ''')
    c.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats (id)
    )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    chats = conn.execute('SELECT * FROM chats WHERE username = ?', (session['username'],)).fetchall()
    conn.close()
    return render_template('index.html', chats=chats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('index'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/create_chat', methods=['POST'])
def create_chat():
    chat_name = request.form['chat_name']
    username = session['username']
    conn = get_db_connection()
    conn.execute('INSERT INTO chats (username, chat_name) VALUES (?, ?)', (username, chat_name))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/chat/<int:chat_id>')
def chat(chat_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    messages = conn.execute('SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp ASC', (chat_id,)).fetchall()
    conn.close()
    return render_template('chat.html', chat_id=chat_id, messages=messages)

@socketio.on('send_message')
def handle_send_message_event(data):
    chat_id = data['chat_id']
    username = session['username']
    message = data['message']
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (chat_id, username, message) VALUES (?, ?, ?)', (chat_id, username, message))
    conn.commit()
    conn.close()
    emit('receive_message', {'chat_id': chat_id, 'username': username, 'message': message}, broadcast=True)

    bot_message = '''Пока на доработке'''
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (chat_id, username, message) VALUES (?, ?, ?)', (chat_id, "Клубочки крючочки", bot_message))
    conn.commit()
    conn.close()
    emit('receive_message', {'chat_id': chat_id, 'username': "Клубочки крючочки", 'message': bot_message}, broadcast=True)

if __name__ == '__main__':
    create_tables()
    socketio.run(app, debug=True)

