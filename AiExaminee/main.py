import os
import json
import uuid
import re
import time
from google.cloud import vision
from langdetect import detect, DetectorFactory
from googletrans import Translator
import streamlit as st
import google.generativeai as genai

# Set up environment variable for Google credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'radiant-striker-422407-b0-3e3a43bf3b7e.json'

# Configure generative AI
GOOGLE_API_KEY = 'AIzaSyAptnflQ56R3qudcZ-KTpvxH7zEHpqVt-8'
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Vision client and translator
vision_client = vision.ImageAnnotatorClient()
translator = Translator()
DetectorFactory.seed = 0

QUIZ_FILE = 'quizzes.json'

def load_quizzes():
    if os.path.exists(QUIZ_FILE):
        with open(QUIZ_FILE, 'r') as file:
            data = json.load(file)
            return {quiz["id"]: quiz for quiz in data["quizzes"]}
    return {}

def save_quizzes(quizzes):
    with open(QUIZ_FILE, 'w') as file:
        data = {"quizzes": list(quizzes.values())}
        json.dump(data, file, indent=4)

quizzes = load_quizzes()

def extract_text_from_image(image_content):
    image = vision.Image(content=image_content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    if response.error.message:
        raise Exception(f'{response.error.message}')
    return texts[0].description if texts else ''

def preprocess_extracted_text(text, primary_language):
    text = re.sub(r'[a-zA-Z0-9]+\s+to\s+[a-zA-Z0-9]+\s+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    words = text.split()
    cleaned_words = []
    for word in words:
        try:
            word_language = detect(word)
        except:
            word_language = None

        if word_language == primary_language:
            cleaned_words.append(word)
        else:
            try:
                translated = translator.translate(word, src=word_language, dest=primary_language).text
                retranslated = translator.translate(translated, src=primary_language, dest=word_language).text
                if word == retranslated:
                    cleaned_words.append(word)
            except:
                continue

    processed_text = ' '.join(cleaned_words)
    return processed_text

def main():
    st.set_page_config(page_title="Quiz System", page_icon="📄", layout="wide")

    st.markdown(
        """
        <style>
        .reportview-container {
            background: #f8f9fa;
            color: #495057;
        }
        .sidebar .sidebar-content {
            background: #343a40;
            color: white;
        }
        h1 {
            color: #343a40;
        }
        .gradient-box {
            border: 4px solid;
            border-image: linear-gradient(to right, #6a11cb, #2575fc) 1;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
            border-radius: 10px;
            animation: gradient-border 2s infinite;
        }
        @keyframes gradient-border {
            0% {
                border-image: linear-gradient(to right, #6a11cb, #2575fc) 1;
            }
            50% {
                border-image: linear-gradient(to right, #2575fc, #6a11cb) 1;
            }
            100% {
                border-image: linear-gradient(to right, #6a11cb, #2575fc) 1;
            }
        }
        .big-button {
            font-size: 1.5em;
            padding: 10px 20px;
            margin: 10px;
            background-color: #6a11cb;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .big-button:hover {
            background-color: #2575fc;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Make a Quiz", "Attend a Quiz"])

    if page == "Home":
        st.title("📄 Quiz System")
        st.markdown("### Welcome! Please choose an option below:")
        st.markdown(
            """
            <div class="gradient-box">
                <h2>Select an Option</h2>
                <button onclick="location.href = '#make_quiz';" class="big-button">Make a Quiz</button>
                <button onclick="location.href = '#attend_quiz';" class="big-button">Attend a Quiz</button>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif page == "Make a Quiz":
        make_quiz()
    elif page == "Attend a Quiz":
        attend_quiz()

def make_quiz():
    st.header("Make a Quiz")
    st.markdown("### Fill out the form below to create your quiz.")

    if "quiz_setup" not in st.session_state:
        st.session_state.quiz_setup = {"name": "", "questions": []}

    with st.form("quiz_form"):
        quiz_name = st.text_input("Quiz Name", value=st.session_state.quiz_setup["name"])
        question = st.text_input("Question")
        answer = st.text_input("Correct Answer")
        marks = st.number_input("Marks", min_value=1, step=1)
        time_limit = st.number_input("Time Limit (seconds)", min_value=10, step=5)
        add_question = st.form_submit_button("Add Question")

        if add_question and quiz_name and question and answer:
            st.session_state.quiz_setup["name"] = quiz_name
            st.session_state.quiz_setup["questions"].append({
                "question": question,
                "answer": answer,
                "marks": marks,
                "time_limit": time_limit
            })
            st.experimental_rerun()

    if st.session_state.quiz_setup["questions"]:
        st.markdown("### Questions")
        for i, q in enumerate(st.session_state.quiz_setup["questions"]):
            st.write(f"**Q{i + 1}:** {q['question']}")
            st.write(f"**Answer:** {q['answer']}")
            st.write(f"**Marks:** {q['marks']}")
            st.write(f"**Time Limit:** {q['time_limit']} seconds")

        if st.button("Submit Quiz"):
            quiz_id = str(uuid.uuid4())
            quizzes[quiz_id] = {
                "id": quiz_id,
                "name": st.session_state.quiz_setup["name"],
                "questions": st.session_state.quiz_setup["questions"]
            }
            save_quizzes(quizzes)
            st.session_state.quiz_setup = {"name": "", "questions": []}
            st.success("Quiz submitted successfully!")
            st.experimental_rerun()

def attend_quiz():
    st.header("Attend a Quiz")
    st.markdown("### Select a quiz to start:")

    quiz_options = {quiz_id: quiz["name"] for quiz_id, quiz in quizzes.items()}
    selected_quiz_id = st.selectbox("Available Quizzes", options=list(quiz_options.keys()), format_func=lambda x: quiz_options[x])

    if selected_quiz_id:
        quiz = quizzes[selected_quiz_id]
        if "quiz_attend" not in st.session_state:
            st.session_state.quiz_attend = {
                "current_quiz": selected_quiz_id,
                "responses": [],
                "time_started": time.time()
            }

        if st.session_state.quiz_attend["current_quiz"] != selected_quiz_id:
            st.session_state.quiz_attend["current_quiz"] = selected_quiz_id
            st.session_state.quiz_attend["responses"] = []
            st.session_state.quiz_attend["time_started"] = time.time()

        total_time_limit = sum([q["time_limit"] for q in quiz["questions"]])
        elapsed_time = time.time() - st.session_state.quiz_attend["time_started"]
        remaining_time = total_time_limit - elapsed_time

        if remaining_time <= 0:
            st.warning("Time is up! Submitting your answers.")
            submit_quiz(quiz)
            return

        st.write(f"Time remaining: {int(remaining_time)} seconds")

        with st.form("quiz_form"):
            for i, question_data in enumerate(quiz["questions"]):
                st.markdown(f"### Question {i + 1}")
                st.markdown(question_data["question"])
                uploaded_file = st.file_uploader(f"Upload an Image for Question {i + 1}", type=["jpg", "jpeg", "png"], key=f"file_{i}")

                if uploaded_file:
                    image_content = uploaded_file.read()
                    extracted_text = extract_text_from_image(image_content)
                    language = detect(extracted_text)
                    processed_text = preprocess_extracted_text(extracted_text, language)
                    st.session_state.quiz_attend["responses"].append({
                        "question_id": i,
                        "response": processed_text
                    })

            if st.form_submit_button("Submit Quiz"):
                submit_quiz(quiz, processed_text)

def submit_quiz(quiz, processed_text=None):
    responses = st.session_state.quiz_attend["responses"]
    feedbacks = []
    total_marks = 0
    total_scored = 0

    for i, question_data in enumerate(quiz["questions"]):
        correct_answer = question_data["answer"]
        response_data = next((resp for resp in responses if resp["question_id"] == i), None)
        response = response_data["response"] if response_data else ""
        model = genai.GenerativeModel()
        prompt = f"""
        Provide feedback for the student's answer based on the correct answer of the question:{question_data['question']}.It carries {question_data['marks']} marks. Evaluate based on understanding and grammar. Understanding has 70% marks and Grammar has 30% marks. Sum the marks and convert to percentage. Behave like a professional teacher of Economics. Give the feedback in bangla. You have to cover the following points: for example(they are just examples)- বোধগম্যতা:3/7, ব্যাকরণ:1/3, মোট:(40%) in one line, and ফিডব্যাক(in 5-10 points) in another line.
        Correct answer: {correct_answer},
        Student Answer: {processed_text}
        """
        feedback = model.generate_content(prompt)
        feedbacks.append(feedback.text)
        scored_marks = re.search(r"মোট:\((\d+)%\)", feedback.text)
        if scored_marks:
            score = int(scored_marks.group(1))
            total_scored += score
        total_marks += question_data["marks"]

    st.markdown("### Quiz Results")
    for i, feedback in enumerate(feedbacks):
        st.markdown(f"**Question {i + 1} Feedback:**")
        st.write(feedback)
    st.write(f"**Total Score:** {total_scored/10}/{total_marks}")

    st.session_state.quiz_attend = {
        "current_quiz": None,
        "responses": [],
        "time_started": None
    }

if __name__ == "__main__":
    main()
