
import os

from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv(override=True)

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        return

    if not api_key.isascii() or any(c.isspace() for c in api_key):
        print("ERROR: GROQ_API_KEY contains invalid characters")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    print("Connecting to Groq...")
    print("Selected model:", model)

    try:
        models = client.models.list()
        available = {item.id for item in models.data}

        if model not in available:
            print("Model was not found in the available model list.")
            print("Check the model ID in Groq Console.")
            return

        print("Model is available.")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a multilingual assistant."
                },
                {
                    "role": "user",
                    "content": "Ответь по-русски: подключение работает?"
                }
            ],
            max_tokens=100
        )

        print("\nGROQ RESPONSE:")
        print(response.choices[0].message.content)

    except Exception as error:
        print("\nERROR:", type(error).__name__)
        print(error)


if __name__ == "__main__":
    main()
