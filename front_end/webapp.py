# webapp.py

import streamlit as st
import sys
import asyncio
from webfeatures import (initialize_session_state, setup_page_config,
                         display_chat, clear_chat, handle_user_input,
                         handle_follow_up)

# Windows event loop policy for asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    initialize_session_state()
    setup_page_config()

    # Handle any pending follow-up questions
    handle_follow_up()

    # Clear chat button
    # Clear chat button (INLINE handling — not a callback)
    if st.button(
        "🧹 Clear Conversation",
        key="clear_chat",
        use_container_width=True,
        help="Start a new conversation"
    ):
        clear_chat()      # just reset state
        st.rerun()        # rerun is safe here


    # Chat display
    display_chat()

    # Chat input
    with st.form(key='chat_form', clear_on_submit=True):
        user_input = st.text_input(
            "Type your message...",
            key="user_input",
            label_visibility="collapsed",
            placeholder="Ask about JSOM programs, admissions, scholarships, etc."
        )
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        handle_user_input(user_input)


if __name__ == "__main__":
    main()
