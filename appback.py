from flask import Flask, render_template, request, redirect, url_for
import json
import random

app = Flask(__name__, static_url_path='/static')
app.secret_key = '68ac36638398af85e7ea06ed024ab074'  # Replace with your secret key

class Quiz:
    def __init__(self, question, options, answer, images=None):
        self.q_no = 0
        self.question = question
        self.options = options
        self.answer = answer
        self.images = images or []  # List of image URLs corresponding to each question
        self.shuffle_questions()
        self.opt_selected = None
        self.correct = 0
        self.data_size = len(self.question)
        self.correct_answers = []

    def shuffle_questions(self):
        combined_data = list(zip(self.question, self.options, self.answer, self.images))
        random.shuffle(combined_data)
        if combined_data:
            self.question, self.options, self.answer, self.images = zip(*combined_data)

    def check_ans(self, q_no):
        return self.opt_selected == self.answer[q_no]

    def next_question(self):
        if self.opt_selected is not None:
            if self.check_ans(self.q_no):
                self.correct += 1
            self.correct_answers.append(self.answer[self.q_no])
            self.q_no += 1
            self.opt_selected = None
            if self.q_no < self.data_size:
                return redirect(url_for('quiz'))
            else:
                return redirect(url_for('result', category=self.category))
        return redirect(url_for('quiz'))

with open('data.json') as f:
    data = json.load(f)

category_percentages = {}  # Dictionary to store percentages per category

@app.route('/')
def index():
    return render_template('category.html')

 
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    global quiz_instance
    selected_category = request.form.get('category')
    if selected_category in data:
        quiz_instance = Quiz(data[selected_category]['question'], data[selected_category]['options'], data[selected_category]['answer'], data[selected_category].get('images', []))
        quiz_instance.category = selected_category
        return redirect(url_for('quiz'))
    else:
        return "Invalid category selected."

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        quiz_instance.opt_selected = int(request.form['choice'])
        return quiz_instance.next_question()

    if quiz_instance.q_no < quiz_instance.data_size:
        current_question = quiz_instance.question[quiz_instance.q_no]
        current_options = quiz_instance.options[quiz_instance.q_no]
        current_image = quiz_instance.images[quiz_instance.q_no] if quiz_instance.images else None
        return render_template('quiz.html', question=current_question, options=current_options, image=current_image)
    else:
        return redirect(url_for('result', category=quiz_instance.category))

@app.route('/result/<category>')
def result(category):
    global category_percentages
    if category not in category_percentages:
        category_percentages[category] = []

    score = int(quiz_instance.correct / quiz_instance.data_size * 100)
    category_percentages[category].append(score)

    return render_template('result.html', score=score, correct_answers=quiz_instance.correct_answers, category=category)

if __name__ == '__main__':
    app.run(debug=True)
