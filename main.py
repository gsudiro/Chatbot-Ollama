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

# Check if messagebox is available
messagebox_available = True
try:
    from tkinter import messagebox
except ImportError:
    messagebox_available = False

class ChatbotGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("AI Chatbot")
        self.window.geometry("920x600")  # Increased width from 800 to 900
        
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.chat_display = ctk.CTkTextbox(self.main_frame, wrap="word")
        self.chat_display.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=3)
        self.chat_display.configure(state="disabled")
        
        # Create model selection frame
        self.model_frame = ctk.CTkFrame(self.main_frame)
        self.model_frame.grid(row=1, column=0, padx=10, pady=(5, 5), sticky="ew")
        self.model_frame.grid_columnconfigure(1, weight=1)
        
        # Model selection from downloaded models
        self.model_var = ctk.StringVar(value="llama3")
        self.model_select = ctk.CTkComboBox(
            self.model_frame,
            variable=self.model_var,
            values=[],
            width=200,
            command=self.on_model_select
        )
        self.model_select.grid(row=0, column=0, padx=5)
        
        # Button to refresh model list - moved next to model selector
        self.refresh_button = ctk.CTkButton(
            self.model_frame,
            text="Refresh List",
            command=self.refresh_models,
            width=100,
            fg_color="#2196F3",  # Blue color to match Send button
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        self.refresh_button.grid(row=0, column=1, padx=5)
        
        # Button to unload model from memory
        self.unload_button = ctk.CTkButton(
            self.model_frame,
            text="Unload Model",
            command=self.unload_model,
            width=100,
            fg_color="#2196F3",  # Blue color
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        self.unload_button.grid(row=0, column=2, padx=5)
        
        # Added Remove button
        self.remove_button = ctk.CTkButton(
            self.model_frame,
            text="Remove Model",
            command=self.remove_model,
            width=100,
            fg_color="#D32F2F",  # Red color for warning
            hover_color="#B71C1C",  # Darker red on hover
            text_color="white"
        )
        self.remove_button.grid(row=0, column=3, padx=5)
        
        # Model name entry for download
        self.model_entry = ctk.CTkEntry(
            self.model_frame, 
            placeholder_text="Model name",
            width=120  # Shortened width
        )
        self.model_entry.grid(row=0, column=4, padx=5)
        
        # Download button
        self.download_button = ctk.CTkButton(
            self.model_frame,
            text="Download",
            command=self.download_model,
            width=80,
            fg_color="#2196F3",  # Blue color to match Send button
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        self.download_button.grid(row=0, column=5, padx=5)
        
        self.see_models_button = ctk.CTkButton(
            self.model_frame,
            text="Browse Models",
            command=lambda: self.open_url("https://ollama.com/search"),
            width=80,
            fg_color="#2196F3",  # Blue color
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        self.see_models_button.grid(row=0, column=6, padx=5)
        
        # Create input frame
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_field = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...")
        self.input_field.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.send_button = ctk.CTkButton(
            self.input_frame, 
            text="Send", 
            command=self.send_message,
            fg_color="#4CAF50",  # Green color
            hover_color="#388E3C",  # Darker green on hover
            text_color="white"
        )
        self.send_button.grid(row=0, column=1)
        
        # Create clear chat button
        self.clear_button = ctk.CTkButton(
            self.input_frame, 
            text="Clear Chat", 
            command=self.clear_chat,
            fg_color="#2196F3",  # Blue color to match Download button
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        self.clear_button.grid(row=0, column=2, padx=(10, 0))
        
        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Initializing...", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="w")
        
        self.input_field.bind("<Return>", lambda event: self.send_message())
        
        # Add shutdown handler to stop Ollama on exit
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.context = ""
        self.chain = None
        self.setup_complete = False
        self.current_model = None
        self.available_models = []
        
        # Start initialization in a separate thread
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
                    self.current_model = models[0]
                self.add_message("System", f"Found {len(models)} installed models")
            else:
                self.add_message("System", "Error fetching installed models")
        except Exception as e:
            self.add_message("System", f"Error refreshing models: {str(e)}")

    def on_model_select(self, choice):
        self.current_model = choice
        self.update_status(f"Selected model: {choice}")
        
        # Load the model into memory
        self.load_model(choice)
    
    def load_model(self, model_name):
        """Load the selected model into memory"""
        self.update_status(f"Loading {model_name} into memory...")
        
        def load():
            try:
                # Create a simple request to load the model
                headers = {"Content-Type": "application/json"}
                data = {
                    "model": model_name,
                    "prompt": " ",  # Minimal prompt just to load the model
                    "stream": False
                }
                
                # Show loading message
                self.add_message("System", f"Loading {model_name} into memory... this may take a moment.")
                
                # Send request to load the model
                response = requests.post("http://localhost:11434/api/generate", 
                                        headers=headers, 
                                        json=data)
                
                if response.status_code == 200:
                    self.update_status(f"Model {model_name} loaded successfully")
                    self.add_message("System", f"{model_name} is now ready to use")
                else:
                    self.update_status(f"Error loading model: {response.text}")
                    self.add_message("System", f"Failed to load {model_name}: {response.text}")
            
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
                self.add_message("System", f"Error loading model: {str(e)}")
        
        # Start loading in a background thread
        threading.Thread(target=load, daemon=True).start()
    
    def unload_model(self):
        model_name = self.current_model
        if not model_name:
            self.add_message("System", "Please select a model to unload")
            return
            
        self.update_status(f"Unloading {model_name} from memory...")
        
        def unload():
            try:
                # Run the ollama command to unload the model
                process = subprocess.Popen(
                    ["ollama", "stop", model_name],  # 'stop' command unloads the model from memory
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    errors='replace',
                    universal_newlines=True
                )
                
                process.wait()
                if process.returncode == 0:
                    self.update_status(f"Model {model_name} unloaded from memory")
                    self.add_message("System", f"Successfully unloaded {model_name} from memory")
                else:
                    error_output = process.stdout.read() if hasattr(process.stdout, 'read') else "Unknown error"
                    self.update_status("Failed to unload model!")
                    self.add_message("System", f"Failed to unload {model_name}: {error_output}")
            except Exception as e:
                self.update_status("Unloading failed!")
                self.add_message("System", f"Error unloading model: {str(e)}")
        
        threading.Thread(target=unload, daemon=True).start()

    def remove_model(self):
        model_name = self.current_model
        if not model_name:
            self.add_message("System", "Please select a model to remove")
            return
            
        # Ask for confirmation before removing
        confirmation_window = ctk.CTkToplevel(self.window)
        confirmation_window.title("Confirm Removal")
        confirmation_window.geometry("400x150")
        confirmation_window.transient(self.window)
        confirmation_window.grab_set()
        
        # Center the window
        confirmation_window.update_idletasks()
        width = confirmation_window.winfo_width()
        height = confirmation_window.winfo_height()
        x = (self.window.winfo_width() // 2) - (width // 2) + self.window.winfo_x()
        y = (self.window.winfo_height() // 2) - (height // 2) + self.window.winfo_y()
        confirmation_window.geometry(f"{width}x{height}+{x}+{y}")
        
        label = ctk.CTkLabel(
            confirmation_window, 
            text=f"Are you sure you want to remove {model_name}?\nThis cannot be undone."
        )
        label.pack(pady=20)
        
        button_frame = ctk.CTkFrame(confirmation_window)
        button_frame.pack(pady=10)
        
        def confirm_remove():
            confirmation_window.destroy()
            self.execute_model_removal(model_name)
            
        confirm_button = ctk.CTkButton(
            button_frame, 
            text="Remove", 
            command=confirm_remove,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            text_color="white"
        )
        confirm_button.pack(side="left", padx=10)
        
        cancel_button = ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=confirmation_window.destroy,
            fg_color="#2196F3",  # Blue color
            hover_color="#1976D2",  # Darker blue on hover
            text_color="white"
        )
        cancel_button.pack(side="left", padx=10)

    def execute_model_removal(self, model_name):
        self.update_status(f"Removing {model_name}...")
        
        def remove():
            try:
                process = subprocess.Popen(
                    ["ollama", "rm", model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    errors='replace',
                    universal_newlines=True
                )
                
                process.wait()
                if process.returncode == 0:
                    self.update_status("Model removed successfully!")
                    self.add_message("System", f"Successfully removed {model_name}")
                    # Refresh model list after removal
                    self.window.after(0, self.refresh_models)
                else:
                    self.update_status("Failed to remove model!")
                    error_output = process.stdout.read() if hasattr(process.stdout, 'read') else "Unknown error"
                    self.add_message("System", f"Failed to remove {model_name}: {error_output}")
            except Exception as e:
                self.update_status("Removal failed!")
                self.add_message("System", f"Error removing model: {str(e)}")
        
        threading.Thread(target=remove, daemon=True).start()

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
                    # Clean the output line of strange characters
                    clean_line = ''.join(c for c in line if c.isprintable() and c not in '\r\x1b')
                    # Remove ANSI escape sequences (often cause display issues)
                    clean_line = self.remove_ansi_escape_sequences(clean_line)
                    if clean_line.strip():  # Only update if there's actual content
                        self.update_status(f"Downloading: {clean_line.strip()}")
                    
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
    
    def remove_ansi_escape_sequences(self, text):
        """Remove ANSI escape sequences from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def get_available_models(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except requests.exceptions.RequestException:
            return []

    def check_disk_usage(self):
        try:
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
        except Exception as e:
            self.add_message("System", f"Error checking disk usage: {str(e)}")

    def update_model_dropdown_state(self, state):
        def update():
            self.model_select.configure(state=state)
            self.refresh_button.configure(state=state)
            self.remove_button.configure(state=state)
            self.unload_button.configure(state=state)
        self.window.after(0, update)

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

    def initialize_chatbot(self):
        self.update_status("Checking Ollama service...")
        if not self.is_ollama_running():
            self.update_status("Starting Ollama service...")
            if not self.start_ollama():
                self.update_status("Error: Could not start Ollama service")
                self.add_message("System", "Error: Could not start Ollama service. Make sure Ollama is installed.")
                return

        self.update_status("Getting available models...")
        self.available_models = self.get_available_models()
        
        if not self.available_models:
            self.update_status("No models found. Downloading llama3 model...")
            self.download_model_with_name("llama3")
            self.available_models = self.get_available_models()
            if not self.available_models:
                self.update_status("Error: Failed to download llama3 model")
                self.add_message("System", "Error: Failed to download llama3 model. Please try downloading a model manually.")
                return
        
        try:
            self.update_status("Initializing AI model...")
            self.model_select.configure(values=self.available_models)
            self.model_select.set(self.available_models[0])
            self.current_model = self.available_models[0]
            
            self.setup_complete = True
            
            self.update_status(f"Ready with model: {self.current_model}")
            self.add_message("System", f"Hello! I'm ready to chat using the {self.current_model} model. How can I help you today?")
            
            # Check disk usage
            self.check_disk_usage()
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.add_message("System", f"Error initializing chatbot: {str(e)}")

    def download_model_with_name(self, model_name):
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
                # Clean the output line of strange characters
                clean_line = ''.join(c for c in line if c.isprintable() and c not in '\r\x1b')
                # Remove ANSI escape sequences
                clean_line = self.remove_ansi_escape_sequences(clean_line)
                if clean_line.strip():  # Only update if there's actual content
                    self.update_status(f"Downloading: {clean_line.strip()}")
                
            process.wait()
            return process.returncode == 0
        except Exception as e:
            self.update_status(f"Error downloading model: {str(e)}")
            return False

    def clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.context = ""
        self.add_message("System", "Chat history cleared.")

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
        self.update_model_dropdown_state("disabled")
        
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
                self.add_message(f"Bot ({self.current_model})", bot_response)
            except Exception as e:
                self.add_message("System", f"Error: {str(e)}")
            finally:
                self.window.after(0, lambda: self.send_button.configure(state="normal"))
                self.window.after(0, lambda: self.update_model_dropdown_state("normal"))

        threading.Thread(target=process_message, daemon=True).start()

    def on_closing(self):
        """Handle application exit event"""
        try:
            # Show exit status message
            self.update_status("Shutting down Ollama...")
            
            # Ask if user wants to stop Ollama on exit
            if messagebox_available:
                from tkinter import messagebox
                stop_ollama = messagebox.askyesno("Exit", "Stop Ollama server when closing?")
            else:
                # Default to yes if messagebox isn't available
                stop_ollama = True
                
            if stop_ollama:
                # Try to stop all running models first
                if self.available_models:
                    for model in self.available_models:
                        try:
                            subprocess.run(["ollama", "stop", model], 
                                        stdout=subprocess.DEVNULL, 
                                        stderr=subprocess.DEVNULL,
                                        timeout=2)
                        except:
                            pass
                
                # Then stop the Ollama service
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/f", "/im", "ollama.exe"], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["pkill", "ollama"], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
        finally:
            # Close the window
            self.window.destroy()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ChatbotGUI()
    app.run()