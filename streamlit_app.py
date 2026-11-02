
import streamlit as st
from contextlib import redirect_stdout
from io import StringIO

from app import SuperChat


st.set_page_config(
    page_title="SuperChat",
    page_icon="💬",
    layout="centered"
)

st.title("💬 SuperChat")
st.caption("Your conversational assistant — Flights, Shopping & Cinema")

if "superchat" not in st.session_state:
    st.session_state.superchat = SuperChat()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("SuperChat")
    st.write("Available domains:")
    st.write("- ✈️ Flights")
    st.write("- 🛍️ Shopping")
    st.write("- 🎬 Cinema")

    if st.button("Start new conversation", use_container_width=True):
        st.session_state.superchat = SuperChat()
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Demo version — uses mock data. No real payments or bookings.")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# User input
prompt = st.chat_input("Ask about flights, products or movies...")

if prompt:
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    output = StringIO()

    try:
        with redirect_stdout(output):
            st.session_state.superchat.handle_message(prompt)

        # Hide internal Router debug messages
        visible_lines = [
            line
            for line in output.getvalue().splitlines()
            if not line.strip().startswith("[Router]")
        ]

        answer = "\n".join(visible_lines).strip()

        if not answer:
            answer = "I couldn't generate a response. Please try again."

    except Exception as error:
        answer = f"Something went wrong: {error}"

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()
