import openai
import json
import re
import os
import tkinter as tk
import psycopg2
from datetime import datetime
from ChatApp import ChatApp
from tkinter import filedialog

os.environ["OPENAI_API_KEY"] = "[Put your API Key Here]"

chatbot = ChatApp()



# Create the Tkinter window
window = tk.Tk()
window.title("GPT App 1")
window.geometry("900x700")





# Create a frame for the conversation widget and add a scrollbar
conversation_frame = tk.Frame(window)
conversation_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
conversation_scrollbar = tk.Scrollbar(conversation_frame)
conversation_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
conversation = tk.Text(conversation_frame, height=30, width=80, wrap="word", yscrollcommand=conversation_scrollbar.set)
conversation.pack(fill=tk.BOTH, expand=True)
conversation_scrollbar.config(command=conversation.yview)

# Create a frame for the input field widget and add a scrollbar
input_frame = tk.Frame(window)
input_frame.pack(fill=tk.X, padx=10, pady=10)
input_scrollbar = tk.Scrollbar(input_frame)
input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
input_field = tk.Text(input_frame, height=5, width=80, yscrollcommand=input_scrollbar.set)
input_field.pack(fill=tk.X, expand=True)
input_scrollbar.config(command=input_field.yview)
# Configure the tag for your messages
conversation.tag_config("you", foreground="blue")

# Adding save to database function
def save_to_database(response):
    conn = None
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(host="192.168.1.130", port=5432, dbname="Chat01", user="agunn", password="443808Cell!")
        
        # Create a cursor object
        cur = conn.cursor()

        # Prepare SQL query
        sql = "INSERT INTO chat_history (timestamp, response) VALUES (%s, %s)"

        # Get the current timestamp
        timestamp = datetime.now()

        # Execute the SQL query
        cur.execute(sql, (timestamp, json.dumps(response)))

        # Commit the changes to the database
        conn.commit()

    except (Exception, psycopg2.DatabaseError) as error:
        print("Error:", error)

    finally:
        if conn is not None:
            conn.close()

# Implement the save_chat() function to save the chat history to a file. You can use the Python json module to serialize the messages to JSON format and write them to a file.
def save_chat():
    filename = tk.filedialog.asksaveasfilename(defaultextension=".json")
    if filename:
        with open(filename, "w") as f:
            json.dump(chatbot.messages, f)

# Implement the load_chat() function to load chat history from a file. You can use the Python json module to deserialize the messages from JSON format and add them to the chatbot.messages list.
def load_chat():
    filename = tk.filedialog.askopenfilename(defaultextension=".json")
    if filename:
        with open(filename, "r") as f:
            chatbot.messages = json.load(f)
        # Clear the conversation widget and add the loaded messages
        conversation.delete("1.0", tk.END)
        for message in chatbot.messages:
            role = message["role"]
            content = message["content"]
            conversation.insert(tk.END, "\n\n" + role.capitalize() + ": " + content)
        conversation.see(tk.END)

def parse_content(content):
    noncode = []
    code = []
    index = 0
    while True:
        start = content.find("```", index)
        if start == -1:
            noncode.append(content[index:])
            break
        noncode.append(content[index:start])
        end = content.find("```", start + 3)
        code.append(content[start + 3:end])
        index = end + 3

    result = []
    for i, text in enumerate(noncode):
        result.append((text, "noncode"))
        if i < len(code):
            result.append((code[i], "code"))

    return result

def clear_chat():
    chatbot.messages = []
    conversation.delete("1.0", tk.END)

def import_data():
    filename = filedialog.askopenfilename()
    if filename:
        with open(filename, "r") as f:
            # Read the contents of the file into a string
            file_contents = f.read()
        # Add the data to the chatbot's messages
        chatbot.messages.append({"role": "system", "content": file_contents})
        # Add the data to the conversation widget
        conversation.insert(tk.END, "\n\nSystem: Here's the data you imported:\n\n")
        conversation.insert(tk.END, file_contents)

# Create a function to handle user input and display the bot's response
def get_response():
    message = input_field.get("1.0", tk.END).strip()
    input_field.delete("1.0", tk.END)
    response = chatbot.chat(message)
    save_to_database(response) # Copy the result to database
    content = response["choices"][0]["message"].content
    parsed_content = parse_content(content)
    conversation.tag_configure("you", foreground="blue", font=("Helvetica", 12,"italic"))
    conversation.insert(tk.END, "\n\nYou: " + message + "\n\n", "you")
    for text, tag in parsed_content:
        conversation.insert(tk.END, text, tag)
        conversation.tag_configure(tag, font=("Arial", 12, "bold") if tag == "code" else ("Arial", 12))
    conversation.see(tk.END)


# Menu for tkinter window to allow load and save files
menu_bar = tk.Menu(window)
file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Save Chat", command=save_chat)
file_menu.add_command(label="Load Chat", command=load_chat)
file_menu.add_separator()
file_menu.add_command(label="Clear Chat", command=clear_chat)
file_menu.add_command(label="Import data", command=import_data)
menu_bar.add_cascade(label="File", menu=file_menu)
window.config(menu=menu_bar)

# Create a button to submit user input and get the bot's response
submit_button = tk.Button(window, text="Submit", command=get_response)
submit_button.pack(padx=10, pady=10)

# Bind the "Ctrl+Return" keystroke to the Submit button
window.bind("<Control-Return>", lambda event: get_response())

# Start the Tkinter mainloop to display the window
window.mainloop()
