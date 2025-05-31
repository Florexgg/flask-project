from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from dotenv import load_dotenv
import openai

load_dotenv()  # Загружаем переменные из .env

openai.api_key = os.getenv("OPENAI_API_KEY")  # Берём ключ из окружения


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

print("API KEY:", os.getenv("OPENAI_API_KEY"))



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
    # Добавляй вопросы по аналогии
]

def get_ai_response(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Ошибка OpenAI:", e)
        return "Извините, произошла ошибка на сервере."
    
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}]
        )
        answer = response.choices[0].message.content
        return jsonify({"reply": answer})
    except Exception as e:
        return jsonify({"reply": "Извините, произошла ошибка на сервере."})

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

    if request.method == 'POST':
        selected = request.form.get('answer')
        if selected is not None and int(selected) == questions[q_id]['answer']:
            session['score'] += 1
        return redirect(url_for('test_question', q_id=q_id + 1))

    question = questions[q_id]
    return render_template('question.html', question=question, q_id=q_id, total=len(questions))

@app.route('/result')
def result():
    score = session.get('score', 0)
    total = len(questions)
    return render_template('result.html', score=score, total=total)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)