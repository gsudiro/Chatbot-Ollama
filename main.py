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
        # Initialize the window
        self.window = ctk.CTk()
        self.window.title("AI Chatbot")
        self.window.geometry("800x600")
        
        # Configure grid layout
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create chat display
        self.chat_display = ctk.CTkTextbox(self.main_frame, wrap="word")
        self.chat_display.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        self.chat_display.configure(state="disabled")
        
        # Create input frame
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Create input field
        self.input_field = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...")
        self.input_field.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        # Create send button
        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1)
        
        # Create models button
        self.models_button = ctk.CTkButton(
            self.input_frame, 
            text="Show Models", 
            command=self.list_installed_models,
            width=100  # Make it smaller than the send button
        )
        self.models_button.grid(row=0, column=2, padx=(10, 0))
        
        # Bind Enter key to send message
        self.input_field.bind("<Return>", lambda event: self.send_message())
        
        # Initialize chatbot components
        self.context = ""
        self.chain = None
        self.setup_complete = False
        
        # Status label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Initializing...", anchor="w")
        self.status_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Start initialization in a separate thread
        threading.Thread(target=self.initialize_chatbot, daemon=True).start()

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

    def check_model_availability(self, model_name):
        try:
            response = requests.get(f"http://localhost:11434/api/tags")
            if response.status_code == 200:
                available_models = response.json().get("models", [])
                return any(model["name"] == model_name for model in available_models)
            return False
        except requests.exceptions.RequestException:
            return False

    def pull_model(self, model_name):
        try:
            # More verbose pulling with real-time output
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            for line in process.stdout:
                self.update_status(f"Downloading: {line.strip()}")
                
            process.wait()
            return process.returncode == 0
        except subprocess.CalledProcessError:
            self.update_status(f"Error pulling {model_name} model")
            return False

    def list_installed_models(self):
        try:
            process = subprocess.Popen(
                ["ollama", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            output = process.communicate()[0]
            if output.strip():
                self.add_message("System", f"Installed models:\n{output}")
            else:
                self.add_message("System", "No models installed yet.")
                
            # Also check disk usage
            if sys.platform == "linux":
                path = "/usr/share/ollama/models"
            elif sys.platform == "darwin":  # macOS
                path = "/usr/local/share/ollama/models"
            elif sys.platform == "win32":
                path = r"C:\ProgramData\ollama\models"
                
            if os.path.exists(path):
                total_size = sum(os.path.getsize(os.path.join(path, f)) 
                               for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)))
                size_gb = total_size / (1024**3)  # Convert to GB
                self.add_message("System", f"Total models size: {size_gb:.2f} GB")
                
        except subprocess.CalledProcessError:
            self.add_message("System", "Error listing models")
        except Exception as e:
            self.add_message("System", f"Error checking models: {str(e)}")

    def initialize_chatbot(self):
        self.update_status("Checking Ollama service...")
        if not self.is_ollama_running():
            self.update_status("Starting Ollama service...")
            if not self.start_ollama():
                self.update_status("Error: Could not start Ollama service")
                return

        self.update_status("Checking model availability...")
        if not self.check_model_availability("llama2"):
            self.update_status("Downloading llama2 model...")
            if not self.pull_model("llama2"):
                self.update_status("Error: Failed to download llama2 model")
                return

        try:
            self.update_status("Initializing AI model...")
            template = """
            Answer the question below.

            Here is the conversation history:
            {context}

            Question: {question}

            Answer:
            """
            model = OllamaLLM(model="llama2")
            prompt = ChatPromptTemplate.from_template(template)
            self.chain = prompt | model
            self.setup_complete = True
            self.update_status("Ready!")
            self.add_message("System", "Hello! I'm ready to chat. How can I help you today?")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")

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

        message = self.input_field.get().strip()
        if not message:
            return

        self.input_field.delete(0, "end")
        self.add_message("You", message)
        self.send_button.configure(state="disabled")
        
        def process_message():
            try:
                result = self.chain.invoke({
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
    ctk.set_appearance_mode("dark")  # Set the theme to dark mode
    ctk.set_default_color_theme("blue")  # Set the color theme
    app = ChatbotGUI()
    app.run()