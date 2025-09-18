# webfeatures.py

import streamlit as st
import sys
import os
import hashlib
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot import JSOMChatbot


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = JSOMChatbot()
    if "pending_follow_up" not in st.session_state:
        st.session_state.pending_follow_up = None


def setup_page_config():
    """Configure page settings."""
    st.set_page_config(page_title="JSOM Assistant", layout="wide")
    st.title("🎓 JSOM Assistant")
    st.markdown("""
        <style>
            .user-message-container {
                width: 50%;
                float: left;
                padding-right: 10px;
            }
            .user-message {
                background-color: #fff3e0; /* Light Yellow */
                padding: 12px;
                border-radius: 10px 10px 0 10px;
                max-width: 95%;
                margin-bottom: 15px;
                clear: both;
            }
            .bot-message-container {
                width: 50%;
                float: right;
                padding-left: 10px;
            }
            .bot-message {
                background-color: #fb8c00; /* Deep Orange */
                color: white; /* Ensure text is readable on the orange background */
                padding: 12px;
                border-radius: 10px 10px 10px 0;
                max-width: 95%;
                margin-bottom: 15px;
                clear: both;
            }
            .clarification-message-container {
                width: 50%;
                float: right;
                padding-left: 10px;
            }
            .clarification-message {
                background-color: #fff3e0;
                border-left: 4px solid #ff9800;
                padding: 12px;
                border-radius: 10px 10px 10px 0;
                max-width: 95%;
                margin-bottom: 15px;
                clear: both;
            }
            .follow-up-container {
                background-color: #e8e8e8;
                padding: 12px;
                border-radius: 8px;
                margin-top: 10px;
                border: 1px solid #d0d0d0;
                width: fit-content; /* Adjust width to content */
                margin-left: 0; /* Align to the left */
                float: left; /* Float to the left */
                clear: both; /* Clear floats */
            }
            .follow-up-title {
                color: #424242;
                font-weight: bold;
                margin-bottom: 8px;
                font-size: 0.9em;
                text-align: left; /* Align title to the left */
            }
            .follow-up-button {
                background-color: #fb8c00;
                color: #424242;
                border: 1px solid #00674f;
                margin: 4px 0;
                border-radius: 6px;
                font-size: 0.9em;
                width: fit-content; /* Adjust button width to content */
                display: block; /* Make buttons stack vertically */
                text-align: left; /* Align button text to the left */
            }
            .stTextInput input {
                border-radius: 20px !important;
                padding: 10px 15px !important;
                background-color: #fff3e0 !important; /* Light Yellow background for input */
            }
            .clear-btn {
                margin-bottom: 15px;
                width: 40%; /* Reduce width of the clear button */
            }
            /* Ensure proper alignment with bot messages */
            .bot-message-container + .follow-up-container {
                margin-left: 0;
            }
        </style>
    """, unsafe_allow_html=True)


def display_chat():
    """Display chat messages with proper styling and follow-up buttons."""
    for msg_idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "User":
            st.markdown(f'<div class="user-message-container"><div class="user-message">{msg["content"]}</div></div>', unsafe_allow_html=True)
        elif msg["role"] == "Assistant":
            message_container_class = "clarification-message-container" if msg.get("needs_clarification", False) else "bot-message-container"
            message_class = "clarification-message" if msg.get("needs_clarification", False) else "bot-message"
            st.markdown(f'<div class="{message_container_class}"><div class="{message_class}">{msg["content"]}</div>', unsafe_allow_html=True)

            if "follow_ups" in msg and msg["follow_ups"] and not msg.get("needs_clarification", False):
                st.markdown('''
                    <div class="follow-up-container">
                        <div class="follow-up-title">You might also ask:</div>
                ''', unsafe_allow_html=True)

                for follow_up_text in msg["follow_ups"]:
                    unique_key = f"follow_up_{msg_idx}_{hashlib.md5(follow_up_text.encode()).hexdigest()}"
                    if st.button(
                            follow_up_text,
                            key=unique_key,
                            help="Click to ask this question",
                            type="primary",
                            use_container_width=False
                    ):
                        st.session_state.pending_follow_up = follow_up_text
                        st.rerun()  # safe here (not in a callback)


                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('</div>', unsafe_allow_html=True)


def clear_chat():
    """Clear chat history and reset chatbot."""
    st.session_state.messages = []
    st.session_state.chatbot = JSOMChatbot()
    # no st.rerun() here


def handle_user_input(user_input):
    """Process user input and generate chatbot response."""
    if user_input.strip():
        chatbot = st.session_state.chatbot
        answer_dict = chatbot.get_answer(user_input)
        follow_up_questions = []
        needs_clarification = False

        response = answer_dict.get("response", "")
        if "You might also be wondering:" in response:
            parts = response.split("You might also be wondering:")
            response_text = parts[0].strip()
            if len(parts) > 1:
                follow_up_lines = parts[1].strip().split("\n")
                for line in follow_up_lines:
                    match = re.match(r'^\d+\.\s*(.*)', line)
                    if match:
                        follow_up_questions.append(match.group(1).strip())
        else:
            response_text = response

        st.session_state.messages.append({
            "role": "User",
            "content": user_input
        })
        st.session_state.messages.append({
            "role": "Assistant",
            "content": response_text,
            "follow_ups": follow_up_questions,
            "needs_clarification": answer_dict.get("needs_clarification", False)
        })

        st.rerun()


def handle_follow_up():
    """Process any pending follow-up questions."""
    if st.session_state.pending_follow_up:
        follow_up = st.session_state.pending_follow_up
        st.session_state.pending_follow_up = None
        handle_user_input(follow_up)
