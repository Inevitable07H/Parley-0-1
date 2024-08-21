import streamlit as st
from PyPDF2 import PdfReader
import requests
from datetime import datetime, timedelta
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("Technowizz7.0/parley01-cb99c-firebase-adminsdk-t8cg8-7e1e56682d.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")

db = firestore.client()

client = Groq(api_key="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")

def extract_text_from_pdf(file_path):
    pdf_reader = PdfReader(file_path)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text

def ai_response(question, text, suspect_name, is_criminal):
    tones = {
        "Eve Davis": "calm and professional",
        "Henry Taylor":"nervous and evasive",
        "Victor Lewis": "confident and manipulative",
        "Xavier Green": "sarcastic and dismissive",
        "Helen Coleman": "manipulative and egoistic"
    }
    tone = tones.get(suspect_name, "neutral")
    
    prompt = f"Assume you are {'the criminal' if is_criminal else 'a suspect'} named {suspect_name} being investigated by detectives Vector Clark and Shaw Chen in a cyberfraud case involving Maria James. You have a {tone} tone. The information about you is: {text[:500]}... The detectives ask: {question}. How do you respond?"

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    if response and response.choices:
        return response.choices[0].message.content.strip()
    else:
        st.error("Error: Could not retrieve response from Groq API.")
        return "Error: Could not retrieve response from Groq API."

def start_timer():
    if "end_time" not in st.session_state:
        st.session_state.end_time = datetime.now() + timedelta(minutes=35)

def check_timer():
    remaining_time = st.session_state.end_time - datetime.now()
    if remaining_time.total_seconds() > 0:
        minutes, seconds = divmod(remaining_time.total_seconds(), 60)
        st.sidebar.write(f"Time remaining: {int(minutes)}:{int(seconds):02d}")
    else:
        st.error("Time's up!")
        st.stop()

def log_attempt(user_data, guess, is_correct):
    try:
        user_data['attempts'].append({
            'guess': guess,
            'is_correct': is_correct,
            'timestamp': datetime.now()
        })

        # Save to Firestore
        db.collection('game_logs').document(user_data['user_id']).set(user_data)

        # Save user data to a local file
        with open(f"{user_data['user_id']}_user_data.json", "w") as outfile:
            json.dump(user_data, outfile, default=str)
        
        st.success("Data saved successfully!")
    except Exception as e:
        st.error(f"Error saving to Firestore: {e}")

# Predefined data
predefined_files = [
    "Technowizz7.0/file-1.pdf", "Technowizz7.0/file-5.pdf", "Technowizz7.0/file-4.pdf", "Technowizz7.0/file-3.pdf", "Technowizz7.0/file-2.pdf"
]

suspect_names = ["Eve Davis", "Helen Coleman" ,"Xavier Green","Victor Lewis","Henry Taylor"]
suspect_images = ["image-1.webp", "image-2.png", "image-3.png", "image-4.jpg", "image-5.webp"]
correct_name = "20" 

# Initialize Streamlit session state
st.set_page_config(page_title="Technowizz7.0")
st.title("Parley0/1")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        'user_id': '',
        'detective1': '',
        'detective2': '',
        'start_time': None,
        'end_time': None,
        'attempts': []
    }
if not st.session_state.logged_in:
    st.subheader("Login Page")
    detective1 = st.text_input("Detective Name-1")
    detective2 = st.text_input("Detective Name-2")
    if st.button("Login"):
        if detective1 and detective2:
            user_id = f"{detective1}_{detective2}_{int(datetime.now().timestamp())}"
            st.session_state.user_data['user_id'] = user_id
            st.session_state.user_data['detective1'] = detective1
            st.session_state.user_data['detective2'] = detective2
            st.session_state.user_data['start_time'] = datetime.now()
            st.session_state.logged_in = True
            st.success("Login successful!")
            
            # Save user data to a local file immediately after login
            with open(f"{st.session_state.user_data['user_id']}_user_data.json", "w") as outfile:
                json.dump(st.session_state.user_data, outfile, default=str)
        else:
            st.error("Please enter both detective names.")
else:
    start_timer()
    check_timer()

    # Initialize session state variables
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {i: [] for i in range(len(predefined_files))}
    if "selected_file_index" not in st.session_state:
        st.session_state.selected_file_index = 0
    if "is_criminal" not in st.session_state:
        st.session_state.is_criminal = [suspect == correct_name for suspect in suspect_names]
    if "name_guesses" not in st.session_state:
        st.session_state.name_guesses = 0
    if "wrong_guesses" not in st.session_state:
        st.session_state.wrong_guesses = 0
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False
    if "input_disabled" not in st.session_state:
        st.session_state.input_disabled = False

    # Display images and text input for suspect name guess
    cols = st.columns(5)
    for i, (suspect_name, suspect_image) in enumerate(zip(suspect_names, suspect_images)):
        with cols[i]:
            if st.button(f"{suspect_name}", key=f"chat_{i}"):
                st.session_state.selected_file_index = i
                st.session_state.chat_open = True
            st.image(suspect_image, use_column_width=True)

    user_guess = st.text_input("Enter the Final Suspect ID:", placeholder="Type the suspect's ID here...",disabled=st.session_state.input_disabled)
    if user_guess and not st.session_state.input_disabled:
        is_correct = user_guess.strip().lower() == correct_name.lower()
        log_attempt(st.session_state.user_data, user_guess, is_correct)
        if is_correct:
            st.success("Correct answer!")
            st.session_state.input_disabled = True
            st.video("https://path_to_success_video.com")
        else:
            st.session_state.wrong_guesses += 1
            if st.session_state.wrong_guesses >= 2:
                st.error("Game over. You've used all your guesses.")
                st.session_state.input_disabled = True
                st.video("https://path_to_failure_video.com")
            else:
                st.error(f"Incorrect guess. You have {2 - st.session_state.wrong_guesses} attempt(s) left.")

    # Chat functionality
    if st.session_state.chat_open:
        selected_file_index = st.session_state.selected_file_index
        selected_file_path = predefined_files[selected_file_index]
        suspect_name = suspect_names[selected_file_index]
        text = extract_text_from_pdf(selected_file_path)
        is_criminal = st.session_state.is_criminal[selected_file_index]

        st.header(f"Chat with Suspect {selected_file_index+1}: {suspect_name}")
        st.subheader("PDF Content")
        st.text(text)

        user_question = st.text_input("Ask a question", key=f"input_{selected_file_index}")
        if user_question:
            st.session_state.chat_history[selected_file_index].append(("User", user_question))
            response = ai_response(user_question, text, suspect_name, is_criminal)
            st.session_state.chat_history[selected_file_index].append((suspect_name, response))

        chat_history = st.session_state.chat_history[selected_file_index]
        for speaker, message in chat_history:
            st.write(f"{speaker}: {message}")

    # Implementing a confirmation to avoid unintentional page refresh
    st.write("""
        <script type="text/javascript">
            window.onbeforeunload = function() {
                return 'Are you sure you want to leave? Your progress will be lost.';
            }
        </script>
    """, unsafe_allow_html=True)
