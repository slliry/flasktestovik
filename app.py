import random
import re
from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Генерируем случайный ключ


def parse_questions(file_path):
    """Парсит файл вопросов в исходном формате."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return []

    # Разделяем по <question>
    raw_questions = content.strip().split('<question>')
    questions = []

    for raw_question in raw_questions:
        if not raw_question.strip():
            continue

        # Получаем текст вопроса
        question_match = re.search(r'(.*?)<variant>', raw_question, re.DOTALL)
        question_text = question_match.group(1).strip() if question_match else raw_question.strip()

        # Получаем варианты ответов
        variants = re.findall(r'<variant>\s*(.+)', raw_question)

        # Перемешиваем варианты
        correct_answer = variants[0]  # Первый вариант — правильный
        random.shuffle(variants)
        correct_index = variants.index(correct_answer)  # Новый индекс правильного ответа

        # Сохраняем вопрос и варианты в структуру
        questions.append({
            "question": question_text,
            "variants": variants,
            "correct": correct_index
        })

    return questions


# Сохраним вопросы в глобальной переменной
ALL_QUESTIONS = parse_questions("questions.txt")


@app.route("/", methods=["GET", "POST"])
def index():
    # Очищаем старые данные сессии
    session.clear()
    
    if request.method == "POST":
        if not ALL_QUESTIONS:
            return "Ошибка загрузки вопросов", 500
            
        # Сохраняем только индексы вопросов вместо полных вопросов
        question_indices = random.sample(range(len(ALL_QUESTIONS)), min(25, len(ALL_QUESTIONS)))
        session["question_indices"] = question_indices
        session["current_index"] = 0
        session["score"] = 0
        return redirect(url_for("quiz"))

    return render_template("index.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    # Проверяем валидность сессии
    if not all(key in session for key in ["question_indices", "current_index", "score"]):
        return redirect(url_for("index"))

    current_index = session["current_index"]
    question_indices = session["question_indices"]
    
    if current_index >= len(question_indices):
        return redirect(url_for("results"))

    # Получаем текущий вопрос по индексу
    question = ALL_QUESTIONS[question_indices[current_index]]
    variants_with_indices = list(enumerate(question["variants"]))

    if request.method == "POST":
        try:
            selected = int(request.form.get("answer", -1))
            session["last_selected"] = question["variants"][selected]
            if selected == question["correct"]:
                session["score"] += 1
        except ValueError:
            pass
            
        session["current_index"] += 1
        session["last_question"] = question["question"]
        session["last_correct"] = question["variants"][question["correct"]]
        return redirect(url_for("feedback"))

    return render_template("quiz.html", 
                         question=question,
                         variants_with_indices=variants_with_indices,
                         index=current_index + 1,
                         total=len(question_indices))


@app.route("/feedback")
def feedback():
    if "last_question" not in session:
        return redirect(url_for("quiz"))
    return render_template("feedback.html", 
                         last_question=session["last_question"],
                         last_correct=session["last_correct"],
                         last_selected=session.get("last_selected", ""))


@app.route("/results")
def results():
    score = session.get("score", 0)
    total = len(session.get("question_indices", []))
    return render_template("results.html", score=score, total=total)


@app.route("/restart")
def restart():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)