import subprocess
import time
import sys
import os
import requests
import customtkinter as ctk
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import threading
from datetime import datetime

class ChatbotGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("AI Chatbot")
        self.window.geometry("800x600")
        
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.chat_display = ctk.CTkTextbox(self.main_frame, wrap="word")
        self.chat_display.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        self.chat_display.configure(state="disabled")
        
        self.model_frame = ctk.CTkFrame(self.main_frame)
        self.model_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        # Model selection from downloaded models
        self.model_var = ctk.StringVar()
        self.model_select = ctk.CTkComboBox(
            self.model_frame,
            variable=self.model_var,
            values=[],
            width=200,
            command=self.on_model_select
        )
        self.model_select.grid(row=0, column=0, padx=5)
        
        # Button to refresh model list
        self.refresh_button = ctk.CTkButton(
            self.model_frame,
            text="Refresh List",
            command=self.refresh_models,
            width=100
        )
        self.refresh_button.grid(row=0, column=1, padx=5)
        
        # Model name entry for download
        self.model_entry = ctk.CTkEntry(
            self.model_frame, 
            placeholder_text="Enter model name to download",
            width=200
        )
        self.model_entry.grid(row=0, column=2, padx=5)
        
        # Download button
        self.download_button = ctk.CTkButton(
            self.model_frame,
            text="Download",
            command=self.download_model,
            width=80
        )
        self.download_button.grid(row=0, column=3, padx=5)
        
        self.see_models_button = ctk.CTkButton(
            self.model_frame,
            text="Browse Models",
            command=lambda: self.open_url("https://ollama.com/search"),
            width=80
        )
        self.see_models_button.grid(row=0, column=4, padx=5)
        
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_field = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...")
        self.input_field.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1)
        
        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Initializing...", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="w")
        
        self.input_field.bind("<Return>", lambda event: self.send_message())
        
        self.context = ""
        self.chain = None
        self.setup_complete = False
        self.current_model = None
        
        threading.Thread(target=self.initialize_chatbot, daemon=True).start()

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def refresh_models(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                self.model_select.configure(values=models)
                if models:
                    self.model_select.set(models[0])
                self.add_message("System", f"Found {len(models)} installed models")
            else:
                self.add_message("System", "Error fetching installed models")
        except Exception as e:
            self.add_message("System", f"Error refreshing models: {str(e)}")

    def on_model_select(self, choice):
        self.current_model = choice
        self.update_status(f"Selected model: {choice}")

    def download_model(self):
        model_name = self.model_entry.get().strip()
        if not model_name:
            self.add_message("System", "Please enter a model name")
            return
            
        self.update_status(f"Downloading {model_name}...")
        
        def download():
            try:
                process = subprocess.Popen(
                    ["ollama", "pull", model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    errors='replace',
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    self.update_status(f"Downloading: {line.strip()}")
                    
                process.wait()
                if process.returncode == 0:
                    self.update_status("Download complete!")
                    self.add_message("System", f"Successfully downloaded {model_name}")
                    self.refresh_models()
                else:
                    self.update_status("Download failed!")
                    self.add_message("System", f"Failed to download {model_name}")
            except Exception as e:
                self.update_status("Download failed!")
                self.add_message("System", f"Error downloading model: {str(e)}")
        
        threading.Thread(target=download, daemon=True).start()

    def initialize_chatbot(self):
        self.update_status("Checking Ollama service...")
        if not self.is_ollama_running():
            self.update_status("Starting Ollama service...")
            if not self.start_ollama():
                self.update_status("Error: Could not start Ollama service")
                return

        self.refresh_models()
        self.setup_complete = True
        self.update_status("Ready!")
        self.add_message("System", "Hello! Select a model to start chatting.")

    def is_ollama_running(self):
        try:
            response = requests.get("http://localhost:11434")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def start_ollama(self):
        try:
            if sys.platform == "win32":
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(["ollama", "serve"], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            
            max_retries = 10
            for i in range(max_retries):
                if self.is_ollama_running():
                    return True
                time.sleep(2)
            return False
        except FileNotFoundError:
            return False

    def update_status(self, status):
        def update():
            self.status_label.configure(text=f"Status: {status}")
        self.window.after(0, update)

    def add_message(self, sender, message):
        def update():
            self.chat_display.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M")
            self.chat_display.insert("end", f"[{timestamp}] {sender}: {message}\n\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
        self.window.after(0, update)

    def send_message(self):
        if not self.setup_complete:
            self.add_message("System", "Please wait until initialization is complete.")
            return

        if not self.current_model:
            self.add_message("System", "Please select a model first.")
            return

        message = self.input_field.get().strip()
        if not message:
            return

        self.input_field.delete(0, "end")
        self.add_message("You", message)
        self.send_button.configure(state="disabled")
        
        def process_message():
            try:
                template = """
                Answer the question below.

                Here is the conversation history:
                {context}

                Question: {question}

                Answer:
                """
                model = OllamaLLM(model=self.current_model)
                chain = ChatPromptTemplate.from_template(template) | model
                
                result = chain.invoke({
                    "context": self.context,
                    "question": message
                })
                bot_response = str(result)
                self.context += f"\nUser: {message}\nAI: {bot_response}"
                self.add_message("Bot", bot_response)
            except Exception as e:
                self.add_message("System", f"Error: {str(e)}")
            finally:
                self.window.after(0, lambda: self.send_button.configure(state="normal"))

        threading.Thread(target=process_message, daemon=True).start()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ChatbotGUI()
    app.run()