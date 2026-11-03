
import streamlit as st
from contextlib import redirect_stdout
from io import StringIO
import re

from app import SuperChat
from integrations.aviasales import AviasalesAPIError


def render_answer(answer: str) -> None:
    """Render Aviasales links as clickable links."""

    rendered_lines = []
    for line in answer.splitlines():
        match = re.match(
            r"^(?P<label>\s*Ссылка Aviasales:\s*)(?P<url>https?://\S+)\s*$",
            line,
        )
        if match:
            url = match.group("url")
            rendered_lines.append(
                f"{match.group('label')}[{url}]({url})"
            )
        elif line.strip().startswith("Ссылка eBay: "):
            url = line.split(":", 1)[1].strip()
            rendered_lines.append(f"[Открыть товар на eBay]({url})")
        elif line.strip().startswith("Изображение: "):
            url = line.split(":", 1)[1].strip()
            rendered_lines.append(f"![Изображение товара]({url})")
        else:
            rendered_lines.append(line)

    st.markdown("\n\n".join(rendered_lines))


st.set_page_config(
    page_title="SuperChat",
    page_icon="💬",
    layout="centered"
)

st.title("💬 SuperChat")
st.caption("Your conversational assistant — Flights, Shopping & Cinema")

if "superchat" not in st.session_state:
    try:
        st.session_state.superchat = SuperChat()
    except AviasalesAPIError as error:
        st.error(f"Aviasales configuration error: {error}")
        st.stop()

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
    st.caption(
        "Flight prices use Aviasales cached Data API data. "
        "No real bookings or payments."
    )

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_answer(message["content"])

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
