from flask import Flask, redirect, url_for, request, session, render_template
from flask_oauthlib.client import OAuth
import json
import random
from flask import jsonify


app = Flask(__name__)
app.secret_key = '68ac36638398af85e7ea06ed024ab074'
oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key='63589803995-1fkussnubluk0e465g29ttbdc83rob4q.apps.googleusercontent.com',
    consumer_secret='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',
    request_token_params={'scope': 'email profile'},
    base_url='https://www.googleapis.com/oauth2/v1/',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
)

class Quiz:
    def __init__(self, question, options, answer, images=None):
        self.q_no = 0
        self.question = question
        self.options = options
        self.answer = answer
        self.images = images or []  # List of image URLs corresponding to each question
        self.correct_images = []  # List of correct image URLs corresponding to each question
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
            self.correct_images = [image for _, _, _, image in combined_data]

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
                return redirect(url_for('result', category=self.category, subcategory=self.subcategory))
        return redirect(url_for('quiz'))

# Load the quiz data from data.json
with open('data.json') as f:
    data = json.load(f)

category_percentages = {}  # Dictionary to store percentages per category

@app.route('/')
def index():
    google_token = session.get('google_token')
    user_email = None

    if google_token:
        user_info = google.get('userinfo')
        user_email = user_info.data['email']

    return render_template('login.html', google_token=google_token, user_email=user_email)

@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
    response = google.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )

    session['google_token'] = (response['access_token'], '')
    user_info = google.get('userinfo')

    # Store or use user information as needed
    user_email = user_info.data['email']

    # Store the profile image URL in the session
    session['profile_image_url'] = user_info.data.get('picture', '')

    # Additional code to run after a successful login
    print(f"User logged in: {user_email}")

    # Redirect to the dashboard route
    return redirect(url_for('dashboard'))

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

# Dictionary to store quiz scores for each user
user_percentages = {}
@app.route('/dashboard')
def dashboard():
    global user_percentages
    google_token = session.get('google_token')

    if google_token:
        user_info = google.get('userinfo')
        user_email = user_info.data['email']
        user_name = user_info.data.get('name', 'Guest')

        # If the user has not taken quizzes before, initialize an empty dictionary
        if user_email not in user_percentages:
            user_percentages[user_email] = {
                "ESAS": {"last_score": 10, "recent_score": 10},
                "EE": {"last_score": 5, "recent_score": 10},
                "MATH": {"last_score": 20, "recent_score": 15},
            }

        # Get all user percentages for the current user
        user_scores = user_percentages.get(user_email, {})

        # Prepare data for the bar graph
        labels_mapping = {'category1': 'ESAS', 'category2': 'EE', 'category3': 'MATH'}
        labels = [labels_mapping.get(category, category) for category in user_scores.keys()]
        data = []

        for category, recent_score in user_scores.items():
            data.append(recent_score)

        # Get the profile image URL from the session
        profile_image_url = session.get('profile_image_url', '')

        return render_template('dashboard.html', user_info=user_info.data, user_name=user_name,
                               user_scores=user_scores, labels=labels, data=data, profile_image_url=profile_image_url)

    else:
        # If the user is not authenticated, redirect to the home page
        return redirect(url_for('index'))



# FOR EXAMINATION TEMPLATE
@app.route('/exam')
def exam():
    google_token = session.get('google_token')

    if google_token:
        user_info = google.get('userinfo')
        user_email = user_info.data['email']
        user_name = user_info.data.get('name', 'Guest')
        # Get the profile image URL from the session
        profile_image_url = session.get('profile_image_url', '')
        return render_template('exam.html', user_info=user_info.data, user_name=user_name, profile_image_url=profile_image_url)
    else:
        # If the user is not authenticated, redirect to the home page
        return redirect(url_for('index'))


@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    global quiz_instance
    selected_category = request.form.get('category')
    selected_subcategory = request.form.get('subcategory')
    
    print(f"Selected Category: {selected_category}, Subcategory: {selected_subcategory}")

    if selected_category in data and selected_subcategory in data[selected_category]:
        quiz_instance = Quiz(
            data[selected_category][selected_subcategory]['question'],
            data[selected_category][selected_subcategory]['options'],
            data[selected_category][selected_subcategory]['answer'],
            data[selected_category][selected_subcategory].get('images', [])
        )
        quiz_instance.category = selected_category
        quiz_instance.subcategory = selected_subcategory
        return redirect(url_for('quiz'))
    else:
        return "Invalid category or subcategory selected."


@app.route('/quiz', methods=['GET', 'POST'])
 
def quiz():
    google_token = session.get('google_token')

    if google_token:
        user_info = google.get('userinfo')
        user_email = user_info.data['email']
        user_name = user_info.data.get('name', 'Guest')

        # Get the profile image URL from the session
        profile_image_url = session.get('profile_image_url', '')

        if request.method == 'POST':
            quiz_instance.opt_selected = int(request.form['choice'])
            return quiz_instance.next_question()

        if quiz_instance.q_no < quiz_instance.data_size:
            # Render the quiz template with the remaining time
            return render_template('quiz.html', question=quiz_instance.question[quiz_instance.q_no],
                                   options=quiz_instance.options[quiz_instance.q_no],
                                   user_info=user_info.data, user_name=user_name,
                                   profile_image_url=profile_image_url,
                                   category=quiz_instance.category, subcategory=quiz_instance.subcategory,
                                   remaining_time=180)  # Set the initial time (3 minutes)
        else:
            return redirect(url_for('result', category=quiz_instance.category, subcategory=quiz_instance.subcategory))

# Dictionary to store quiz scores for each user
user_percentages = {}


def initialize_quiz_instance(category, subcategory):
    global quiz_instance, data

    if category in data and subcategory in data[category]:
        quiz_instance = Quiz(
            data[category][subcategory]['question'],
            data[category][subcategory]['options'],
            data[category][subcategory]['answer'],
            data[category][subcategory].get('images', [])
        )
        quiz_instance.category = category
        quiz_instance.subcategory = subcategory
    else:
        quiz_instance = None

# result route
@app.route('/result/<category>/<subcategory>')
def result(category, subcategory):
    global user_percentages, quiz_instance
    google_token = session.get('google_token')

    if google_token:
        user_info = oauth.google.get('userinfo')
        user_email = user_info.data['email']

       # Calculate the current score
        score = int(quiz_instance.correct / quiz_instance.data_size * 100)

        # If the user has not taken quizzes before, initialize an empty dictionary
        if user_email not in user_percentages:
            user_percentages[user_email] = {}

        # If 'recent_score' key is not present, initialize it
        if 'recent_score' not in user_percentages[user_email]:
            user_percentages[user_email]['recent_score'] = 0

        # Update the user's quiz scores for the current category and subcategory
        user_percentages[user_email]['last_score'] = user_percentages[user_email]['recent_score']
        user_percentages[user_email]['recent_score'] = score

        # Save the updated user percentages to a JSON file
        with open('user_percentage_data.json', 'w') as f:
            json.dump(user_percentages, f)

        # Rest of your existing code...
        correct_questions = quiz_instance.question
        correct_values = quiz_instance.answer
        correct_images = quiz_instance.images

        # Get the profile image URL from the session
        profile_image_url = session.get('profile_image_url', '')

        # Check if the user's score is below 50%
        if score < 50:
            return render_template('result.html', user_info=user_info.data, user_name=user_info.data.get('name', 'Guest'), score=score,
                                   correct_questions=correct_questions, correct_values=correct_values,
                                   correct_images=correct_images,
                                   correct_answers=quiz_instance.correct_answers, category=category,
                                   profile_image_url=profile_image_url,
                                   last_score=user_percentages[user_email]['last_score'],
                                   recent_score=user_percentages[user_email]['recent_score'])

        # If the user's score is 50% or above, proceed to show the result
        return render_template('result.html', user_info=user_info.data, user_name=user_info.data.get('name', 'Guest'), score=score,
                               correct_questions=correct_questions, correct_values=correct_values,
                               correct_images=correct_images,
                               correct_answers=quiz_instance.correct_answers, category=category,
                               profile_image_url=profile_image_url,
                               last_score=user_percentages[user_email]['last_score'],
                               recent_score=user_percentages[user_email]['recent_score'])

    else:
        # If the user is not authenticated, redirect to the home page
        return redirect(url_for('index'))


@app.route('/load_another_set', methods=['POST'])
def load_another_set():
    global quiz_instance  # Assuming quiz_instance is a global variable

    # Determine the next subcategory based on user performance
    selected_category = quiz_instance.category
    if selected_category not in data:
        return "Invalid category selected."

    subcategory1 = 'subcategory1'
    subcategory2 = 'subcategory2'

    # Check if the user has already failed for the current subcategory
    current_subcategory = quiz_instance.subcategory
    if current_subcategory == subcategory1:
        next_subcategory = subcategory2
    else:
        next_subcategory = subcategory1

    # Load questions for the next subcategory
    if next_subcategory in data[selected_category]:
        quiz_instance = Quiz(
            data[selected_category][next_subcategory]['question'],
            data[selected_category][next_subcategory]['options'],
            data[selected_category][next_subcategory]['answer'],
            data[selected_category][next_subcategory].get('images', [])
        )
        quiz_instance.category = selected_category
        quiz_instance.subcategory = next_subcategory

        return redirect(url_for('quiz'))  # Redirect to the quiz route to start another set of questions

    return f"No questions found for {selected_category} - {next_subcategory}."

    #  print the question and choices

 
# @app.route('/print_questions')
# Initialize quiz_instance variable
quiz_instance = None


@app.route('/print_questions')
def print_questions():
    google_token = session.get('google_token')

    if google_token:
        user_info = oauth.google.get('userinfo')
        user_email = user_info.data['email']
        # Ensure 'data' is defined and has questions
        if 'data' not in globals() or not data:
            return "No questions found in data.json."

        # Retrieve user_info from the session
        user_info = session.get('user_info')

        all_questions = []

        # Iterate over categories and subcategories
        for category, subcategories in data.items():
            for subcategory, questions_data in subcategories.items():
                questions = questions_data.get('question', [])
                options = questions_data.get('options', [])

                # Zip questions and options together for display
                for q, o in zip(questions, options):
                    all_questions.append({'question': q, 'options': o})

        # return render_template('print_questions.html', all_questions=all_questions, user_info=user_info, user_name=user_info.get('name', 'Guest'))
        return render_template('print_questions.html', all_questions=all_questions, user_info=user_info)

if __name__ == '__main__':
    app.run(debug=True)
