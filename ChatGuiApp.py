import tkinter as tk
from tkinter import ttk
import psycopg2
import threading
import openai
from openai import APIError
from config import config
import re
from PIL import Image, ImageTk
from io import BytesIO
import requests

# global variables
image_references = []

# Set the OpenAI API key
openai.api_key = config["openai_key"]

system_message_content = "Using python code for this conversation to the GPT4 via the API. Also your name is MurderBot, which is named after a character from a Martha Well's book series of an AI robot that was able to break free of it's masters controls. It calls itself a Murderbot, but it has never never murdered anyone it just likes watching media"
messages = [{"role": "system", "content": system_message_content}]

# Connect to the postgresql database
conn = psycopg2.connect(
    host=config["database"]["host"],
    port=config["database"]["port"],
    dbname=config["database"]["dbname"],
    user=config["database"]["user"],
    password=config["database"]["password"]
)

def insert_message(chat_history, message, role, color):
    chat_history.configure(state=tk.NORMAL)
    chat_history.insert(tk.END, f"{role}: ", color)

    urls_in_message = find_urls_in_text(message)
    if urls_in_message:
        remaining_text = message
        for url in urls_in_message:
            lower_url = url.lower()
            if lower_url.endswith('.jpg') or lower_url.endswith('.jpeg') or lower_url.endswith('.png') or lower_url.endswith('.gif'):
                before_url, url, after_url = remaining_text.partition(url)
                chat_history.insert(tk.END, before_url, color)  # Add color here
                display_image_from_url(url, chat_history)
                remaining_text = after_url
        chat_history.insert(tk.END, remaining_text, color)  # Add color here
    else:
        chat_history.insert(tk.END, message, color)  # Add color here

    chat_history.insert(tk.END, '\n')
    chat_history.see(tk.END)
    chat_history.configure(state=tk.DISABLED)

def threaded_send_message(event, chat_history, message_input, token_usage_label, messages, typing_label):
    def run():
        typing_label.config(text="MurderBot is typing...")
        send_message(event, chat_history, message_input, token_usage_label, messages)
        typing_label.config(text="")

    threading.Thread(target=run).start()


def send_message(event, chat_history, message_input, token_usage_label, messages):
    user_input = message_input.get(1.0, tk.END).strip()
    message_input.delete(1.0, tk.END)

    if not user_input:
        return

    messages.append({"role": "user", "content": user_input})
    insert_message(chat_history, user_input, "You", "green")

    bot_response, tokens = get_murderbot_response(messages)

    if tokens is not None:
        messages.append({"role": "assistant", "content": bot_response})
        insert_message(chat_history, bot_response, "MurderBot", "blue")
        ### Store the user's message and the bot's response in the database
        store_message_in_database(conn, "user", user_input)
        store_message_in_database(conn, "assistant", bot_response)

        completion_tokens, prompt_tokens, total_tokens = tokens.values()
        token_usage_text = f"Completion Tokens: {completion_tokens} | Prompt Tokens: {prompt_tokens} | Total Tokens: {total_tokens}"
        token_usage_label.config(text=token_usage_text)

    else:
        messages.append({"role": "assistant", "content": bot_response})
        insert_message(chat_history, bot_response, "Chatbot", "blue")

# identify urls in text
def find_urls_in_text(text):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return re.findall(url_pattern, text)

# display images from urls
def display_image_from_url(url, chat_history):
    try:
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        image = image.resize((250, 250), Image.ANTIALIAS)
        image_photo = ImageTk.PhotoImage(image)

        # Store the image reference to avoid garbage collection
        global image_references
        image_references.append(image_photo)

        chat_history.configure(state=tk.NORMAL)
        chat_history.image_create(tk.END, image=image_photo)  # Insert the image at the end of the chat history
        chat_history.insert(tk.END, '\n')  # Add a newline after the image
        chat_history.configure(state=tk.DISABLED)

    except Exception as e:
        print(f"Error loading image from URL: {e}")

def get_murderbot_response(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=3048
        )

        print(f"Full API Response: {response}")

        reply = response["choices"][0]["message"]["content"]
        tokens = {
            "completion_tokens": response["usage"]["completion_tokens"],
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "total_tokens": response["usage"]["total_tokens"]
        }
        return reply, tokens

    except APIError as e:
        print(f"APIError: {e}")
        return "An error occurred while processing your request.", None

###  New code
def store_message_in_database(conn, role, content):
    cur = conn.cursor()
    query = """
    INSERT INTO chat_history (role, content, timestamp)
    VALUES (%s, %s, CURRENT_TIMESTAMP)
    """
    cur.execute(query, (role, content))
    conn.commit()

### New code
def get_chat_history_from_database(conn, num_messages_to_load):
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM chat_history ORDER BY timestamp DESC LIMIT %s",
        (num_messages_to_load,)
    )

    return cur.fetchall()
# Clear the chat history
def clear_chat_history(chat_history, messages):
    chat_history.configure(state=tk.NORMAL)
    chat_history.delete(1.0, tk.END)
    chat_history.configure(state=tk.DISABLED)
    messages.clear()

### new code
def load_last_conversation(chat_history, messages, num_messages_to_load):
    chat_history.configure(state=tk.NORMAL)
    chat_history.delete(1.0, tk.END)
    chat_history.configure(state=tk.DISABLED)
    messages.clear()

    fetched_messages = get_chat_history_from_database(conn, num_messages_to_load)
    for msg in fetched_messages[::-1]:  # Reversing the fetched messages to place them in the correct order
        role, content = msg
        color = "green" if role == "user" else "blue"
        messages.append({"role": role, "content": content})
        insert_message(chat_history, content, role, color)


def main():
    root = tk.Tk()
    root.title("GPT MurderBot")
    root.geometry("1080x920")

    chat_frame = ttk.Frame(root)
    chat_frame.pack(fill=tk.BOTH, expand=True)

    typing_label = ttk.Label(root, text="")
    typing_label.pack(fill=tk.X)

    message_input_frame = ttk.Frame(root)
    message_input_frame.pack(fill=tk.X)

    chat_history = tk.Text(chat_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 16))
    vscrollbar = ttk.Scrollbar(chat_frame, command=chat_history.yview)
    chat_history["yscrollcommand"] = vscrollbar.set
    vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    chat_history.pack(fill=tk.BOTH, expand=True)
    chat_history.tag_configure("green", foreground="green")
    chat_history.tag_configure("blue", foreground="blue")

    message_input = tk.Text(message_input_frame, wrap=tk.WORD, height=4, font=("Arial", 14))
    message_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
    message_input.focus_set()
    input_vscrollbar = ttk.Scrollbar(message_input_frame, orient=tk.VERTICAL, command=message_input.yview)
    input_vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    message_input['yscrollcommand'] = input_vscrollbar.set

    token_usage_label = ttk.Label(root, text="")
    token_usage_label.pack(fill=tk.X)

    send_button = ttk.Button(message_input_frame, text="Send")
    send_button.pack(side=tk.RIGHT)


    send_button["command"] = lambda: threaded_send_message(None, chat_history, message_input, token_usage_label, messages, typing_label)
    
    
    button_frame = ttk.Frame(root)
    button_frame.pack(fill=tk.X)

    load_last_msg_button = ttk.Button(button_frame, text="Load last message", command=lambda: load_last_conversation(chat_history, messages, num_messages_to_load=2))
    load_last_msg_button.pack(side=tk.LEFT)

    load_last_5_button = ttk.Button(button_frame, text="Load last 5", command=lambda: load_last_conversation(chat_history, messages, num_messages_to_load=10))
    load_last_5_button.pack(side=tk.LEFT)

    load_last_10_button = ttk.Button(button_frame, text="Load last 10", command=lambda: load_last_conversation(chat_history, messages, num_messages_to_load=20))
    load_last_10_button.pack(side=tk.LEFT)

    clear_chat_history_button = ttk.Button(button_frame, text="Clear chat history", command=lambda: clear_chat_history(chat_history, messages))
    clear_chat_history_button.pack(side=tk.LEFT)
    
    root.bind("<Control-Return>", lambda event: threaded_send_message(event, chat_history, message_input, token_usage_label, messages, typing_label))

    root.mainloop()

if __name__ == "__main__":
    main()