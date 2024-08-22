import streamlit as st
from PyPDF2 import PdfReader
from datetime import datetime, timedelta
import json
import os
from groq import Groq

# Initialize Groq API client
def initialize_groq():
    return Groq(api_key="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")

client = initialize_groq()

# Function to extract text from a PDF file
def extract_text_from_pdf(file_path):
    pdf_reader = PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to get AI response using Groq API
def ai_response(question, text, suspect_name, is_criminal):
    tones = {
        "Eve Davis": "calm and professional",
        "Henry Taylor": "nervous and evasive",
        "Victor Lewis": "confident and manipulative",
        "Xavier Green": "sarcastic and dismissive",
        "Helen Coleman": "manipulative and egoistic"
    }
    tone = tones.get(suspect_name, "neutral")
    
    prompt = f"Assume you are {'the criminal' if is_criminal else 'a suspect'} named {suspect_name} being investigated by detectives Vector Clark and Shaw Chen in a cyberfraud case involving Maria James. You have a {tone} tone. The information about you is: {text[:500]}... The detectives ask: {question}. How do you respond?"

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        if response and response.choices:
            return response.choices[0].message.content.strip()
        else:
            st.error("Error: Could not retrieve response from Groq API.")
            return "Error: Could not retrieve response from Groq API."
    except Exception as e:
        st.error(f"API request failed: {e}")
        return "Error: Could not retrieve response from Groq API."

# Timer functions
def start_timer():
    if "end_time" not in st.session_state:
        st.session_state.end_time = datetime.now() + timedelta(minutes=35)

def check_timer():
    remaining_time = st.session_state.end_time - datetime.now()
    if remaining_time.total_seconds() > 0:
        minutes, seconds = divmod(remaining_time.total_seconds(), 60)
        st.sidebar.write(f"Time remaining: {int(minutes)}:{int(seconds):02d}")
        st.sidebar.write(f"\nThis is the Parley's time which only changes whenever you interact with any of the suspects.")
    else:
        st.error("Time's up!")
        st.stop()

# Function to log attempts
def log_attempt(user_data, guess, is_correct):
    try:
        user_data['attempts'].append({
            'guess': guess,
            'is_correct': is_correct,
            'timestamp': datetime.now()
        })

        # Save user data to a local file
        with open(f"{user_data['user_id']}_user_data.json", "w") as outfile:
            json.dump(user_data, outfile, default=str)
        
        st.success("Data saved successfully!")
    except Exception as e:
        st.error(f"Error saving data: {e}")

# Predefined data
predefined_files = [
    "Technowizz7.0/file-1.pdf", "Technowizz7.0/file-5.pdf", "Technowizz7.0/file-4.pdf", "Technowizz7.0/file-3.pdf", "Technowizz7.0/file-2.pdf"
]

suspect_names = ["Eve Davis", "Helen Coleman", "Xavier Green", "Victor Lewis", "Henry Taylor"]
suspect_images = ["Technowizz7.0/image-1.webp", "Technowizz7.0/image-2.png", "Technowizz7.0/image-3.png", "Technowizz7.0/image-4.jpg", "Technowizz7.0/image-5.webp"]
correct_name = "20"  # Correct suspect's name

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
if "login_attempted" not in st.session_state:
    st.session_state.login_attempted = False

if not st.session_state.logged_in and not st.session_state.login_attempted:
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
            st.session_state.login_attempted = True
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
        st.session_state.is_criminal = [suspect_name == correct_name for suspect_name in suspect_names]
    if "name_guesses" not in st.session_state:
        st.session_state.name_guesses = 0
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

    user_guess = st.text_input("Enter the Final Suspect Id:", placeholder="Enter the Suspect ID here", disabled=st.session_state.input_disabled)
    if user_guess and not st.session_state.input_disabled:
        is_correct = (user_guess.lower() == correct_name.lower())  # Case-insensitive comparison
        log_attempt(st.session_state.user_data, user_guess, is_correct)
        if is_correct:
            st.success("Correct answer!")
            st.session_state.input_disabled = True
            st.video("Technowizz7.0/Add a heading (5).mp4", start_time=0)  # Automatically start the success video
        else:
            st.error("Game over. You've used your only guess.")
            st.session_state.input_disabled = True
            st.video("Technowizz7.0/Add a heading (6).mp4", start_time=0)  # Automatically start the failure video

    # Chat functionality
    if st.session_state.chat_open:
        selected_file_index = st.session_state.selected_file_index
        selected_file_path = predefined_files[selected_file_index]
        suspect_name = suspect_names[selected_file_index]
        text = extract_text_from_pdf(selected_file_path)
        is_criminal = st.session_state.is_criminal[selected_file_index]

        st.header(f"Chat with Suspect {selected_file_index + 1}: {suspect_name}")
        st.subheader("PDF Content")
        st.text(text)

        user_question = st.text_input("Ask a question", key=f"input_{selected_file_index}")
        if user_question:
            st.session_state.chat_history[selected_file_index].append(("User", user_question))
            response = ai_response(user_question, text, suspect_name, is_criminal)
            st.session_state.chat_history[selected_file_index].append((suspect_name, response))

        # Display chat history
        for speaker, message in st.session_state.chat_history[selected_file_index]:
            st.write(f"**{speaker}:** {message}")
