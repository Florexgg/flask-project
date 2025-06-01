from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import random
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import re

load_dotenv()

print("EMAIL_USER =", os.getenv('EMAIL_USER'))
print("EMAIL_PASS =", os.getenv('EMAIL_PASS'))

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER')

app.config.update(
    MAIL_SERVER='smtp.yandex.ru',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.getenv('EMAIL_USER'),
    MAIL_PASSWORD=os.getenv('EMAIL_PASS'),
    MAIL_DEFAULT_SENDER=os.getenv('EMAIL_USER')
)

verification_codes = {}  # email: code

mail = Mail(app)

questions = [
    {
        'question': 'Что такое фишинг?',
        'options': ['Вирус', 'Мошенничество', 'Хакерская атака', 'Антивирус'],
        'answer': 1
    },
    {
        'question': 'Как защитить пароль?',
        'options': ['Писать на бумажке', 'Использовать сложный пароль', 'Делиться с друзьями', 'Не менять никогда'],
        'answer': 1
    },
    {
        'question': 'Что такое двухфакторная аутентификация?',
        'options': ['Второй аккаунт', 'Запасной пароль', 'Дополнительный уровень защиты', 'Форма обратной связи'],
        'answer': 2
    },
    {
        'question': 'Какой сайт безопаснее?',
        'options': ['http://example.com', 'https://example.com'],
        'answer': 1
    },
    {
        'question': 'Что делать, если получил подозрительное письмо?',
        'options': ['Открыть вложение', 'Ответить на письмо', 'Удалить и сообщить', 'Переслать друзьям'],
        'answer': 2
    },
    {
        'question': 'Зачем нужен антивирус?',
        'options': ['Украсть данные', 'Замедлить ПК', 'Защитить от угроз', 'Удалить программы'],
        'answer': 2
    },
    {
        'question': 'Что такое спам?',
        'options': ['Полезные уведомления', 'Нежелательные письма', 'Служебная почта', 'Сообщения от друзей'],
        'answer': 1
    },
    {
        'question': 'Как часто нужно обновлять пароли?',
        'options': ['Никогда', 'Раз в год', 'Раз в месяц или при утечке', 'Каждую неделю'],
        'answer': 2
    },
    {
        'question': 'Можно ли использовать один пароль для всех сайтов?',
        'options': ['Да', 'Нет', 'Только для соцсетей', 'Если не забываешь — можно'],
        'answer': 1
    },
    {
        'question': 'Что делать при подозрении на взлом аккаунта?',
        'options': ['Ничего', 'Сменить пароль и включить 2FA', 'Удалить аккаунт', 'Сообщить друзьям'],
        'answer': 1
    },
    {
        'question': 'Безопасно ли подключаться к Wi-Fi в кафе?',
        'options': ['Да', 'Нет, если нет VPN', 'Только ночью', 'Если пароль "123456"'],
        'answer': 1
    },
    {
        'question': 'Какие файлы нельзя скачивать из интернета?',
        'options': ['Документы', '.exe от неизвестных источников', 'Фото друзей', 'PDF-файлы с расписанием'],
        'answer': 1
    }
]

# База данных
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')

    # НОВАЯ таблица результатов
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            total INTEGER,
            taken_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        if not email or not password:
            error = "Введите email и пароль"
            return render_template('login.html', error=error)

        # <-- создаем соединение и курсор ДО того как вызываем c.execute
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute('SELECT id, name, password FROM users WHERE email=?', (email,))
        result = c.fetchone()
        conn.close()

        if result and check_password_hash(result[2], password):
            session['user'] = email
            session['user_id'] = result[0]
            session['name'] = result[1]
            return redirect(url_for('index'))
        else:
            error = "Неверный email или пароль."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('name', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        raw_password = request.form.get('password')

        # --- ВАЛИДАЦИЯ ПАРОЛЯ ---
        if not re.match(r'^[A-Za-z0-9]{8,}$', raw_password):
            # error = "Пароль должен содержать минимум 8 символов, только латинские буквы и цифры."
            return render_template('register.html', error=error)

        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$', raw_password):
            # error = "Пароль должен содержать минимум 8 символов, хотя бы одну заглавную, одну строчную и одну цифру."
            return render_template('register.html', error=error)

        password = generate_password_hash(raw_password)

        code = str(random.randint(100000, 999999))
        verification_codes[email] = {'code': code, 'password': password, 'name': name}

        msg = Message("Код подтверждения", recipients=[email])
        msg.body = f"Ваш код подтверждения: {code}"
        mail.send(msg)

        return redirect(url_for('verify_email', email=email))

    return render_template('register.html', error=error)

@app.route('/verify/<email>', methods=['GET', 'POST'])
def verify_email(email):
    error = ""
    if request.method == 'POST':
        user_code = request.form['code']
        expected = verification_codes.get(email)

        if expected and user_code == expected['code']:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()

            # Проверяем, есть ли уже такой email
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            if c.fetchone():
                conn.close()
                error = "Пользователь с таким email уже существует."
                return render_template('verify.html', email=email, error=error)

            # Если email свободен — регистрируем
            c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                    (expected['name'], email, expected['password']))
            conn.commit()
            conn.close()

            verification_codes.pop(email)
            return redirect('/login')
        else:
            error = "Неверный код подтверждения"

    return render_template('verify.html', email=email, error=error)

@app.route('/')
def index():
    return render_template('index.html')  # Главная страница

@app.route('/rules')
def rules():
    return render_template('rules.html')  # Правила

@app.route('/test')
def test_start():
    session['score'] = 0
    return redirect(url_for('test_question', q_id=0))

@app.route('/test/<int:q_id>', methods=['GET', 'POST'])
def test_question(q_id):
    if q_id < 0 or q_id >= len(questions):
        return redirect(url_for('result'))

    if 'score' not in session:
        session['score'] = 0

    question = questions[q_id]
    selected = None
    show_result = False

    if request.method == 'POST':
        submitted = request.form.get('submitted')

        if submitted == 'answer':
            selected = request.form.get('answer')
            if selected is not None and int(selected) == question['answer']:
                session['score'] += 1
            show_result = True
        elif submitted == 'next':
            return redirect(url_for('test_question', q_id=q_id + 1))

    return render_template(
        'question.html',
        question=question,
        q_id=q_id,
        total=len(questions),
        selected=selected,
        correct=question['answer'],
        show_result=show_result
    )


@app.route('/result')
def result():
    score = session.get('score', 0)
    total = len(questions)

    user_id = session.get("user_id")  # ← достаём ID пользователя

    if user_id:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO test_results (user_id, score, total, taken_at) VALUES (?, ?, ?, ?)",
            (user_id, score, total, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    return render_template('result.html', score=score, total=total)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    init_db()
    app.run(debug=True)
