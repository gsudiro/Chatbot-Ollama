import subprocess
import time
import sys
import os
import re
import json
import threading
from datetime import datetime
from tkinter import messagebox
import webbrowser

import requests
import customtkinter as ctk
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate


class ChatbotGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("AI Chatbot")
        self.window.geometry("920x600")
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.main_frame, wrap="word")
        self.chat_display.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=3)
        self.chat_display.configure(state="disabled")

        # Model selection frame
        self.model_frame = ctk.CTkFrame(self.main_frame)
        self.model_frame.grid(row=1, column=0, padx=10, pady=(5, 5), sticky="ew")
        self.model_frame.grid_columnconfigure(1, weight=1)

        self.model_var = ctk.StringVar(value="llama3")
        self.model_select = ctk.CTkComboBox(
            self.model_frame,
            variable=self.model_var,
            values=[],
            width=200,
            command=self.on_model_select
        )
        self.model_select.grid(row=0, column=0, padx=5)

        self.refresh_button = ctk.CTkButton(
            self.model_frame,
            text="Refresh List",
            command=self.refresh_models,
            width=100,
            fg_color="#2196F3",
            hover_color="#1976D2",
            text_color="white"
        )
        self.refresh_button.grid(row=0, column=1, padx=5)

        self.unload_button = ctk.CTkButton(
            self.model_frame,
            text="Unload Model",
            command=self.unload_model,
            width=100,
            fg_color="#2196F3",
            hover_color="#1976D2",
            text_color="white"
        )
        self.unload_button.grid(row=0, column=2, padx=5)

        self.remove_button = ctk.CTkButton(
            self.model_frame,
            text="Remove Model",
            command=self.remove_model,
            width=100,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            text_color="white"
        )
        self.remove_button.grid(row=0, column=3, padx=5)

        self.model_entry = ctk.CTkEntry(
            self.model_frame,
            placeholder_text="Model name",
            width=120
        )
        self.model_entry.grid(row=0, column=4, padx=5)

        self.download_button = ctk.CTkButton(
            self.model_frame,
            text="Download",
            command=self.download_model,
            width=80,
            fg_color="#2196F3",
            hover_color="#1976D2",
            text_color="white"
        )
        self.download_button.grid(row=0, column=5, padx=5)

        self.see_models_button = ctk.CTkButton(
            self.model_frame,
            text="Browse Models",
            command=lambda: self.open_url("https://ollama.com/search "),
            width=80,
            fg_color="#2196F3",
            hover_color="#1976D2",
            text_color="white"
        )
        self.see_models_button.grid(row=0, column=6, padx=5)

        # Input frame
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.input_field = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...")
        self.input_field.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self.send_message,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            text_color="white"
        )
        self.send_button.grid(row=0, column=1)

        self.clear_button = ctk.CTkButton(
            self.input_frame,
            text="Clear Chat",
            command=self.clear_chat,
            fg_color="#2196F3",
            hover_color="#1976D2",
            text_color="white"
        )
        self.clear_button.grid(row=0, column=2, padx=(10, 0))

        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Initializing...", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="w")

        # Download progress frame
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.grid(row=4, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="", anchor="w")
        self.progress_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        self.cancel_download_button = ctk.CTkButton(
            self.progress_frame,
            text="Cancel",
            command=self.cancel_download,
            width=80,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            text_color="white"
        )
        self.cancel_download_button.grid(row=0, column=1, padx=5, pady=5)

        self.progress_frame.grid_remove()

        self.input_field.bind("<Return>", lambda event: self.send_message())
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.context = ""
        self.chain = None
        self.setup_complete = False
        self.current_model = None
        self.available_models = []
        self.download_process = None
        self.download_cancel_requested = False

        threading.Thread(target=self.initialize_chatbot, daemon=True).start()

    def open_url(self, url):
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
        self.load_model(choice)

    def load_model(self, model_name):
        """Load the selected model into memory"""
        self.update_status(f"Loading {model_name} into memory...")

        def load():
            try:
                headers = {"Content-Type": "application/json"}
                data = {
                    "model": model_name,
                    "prompt": " ",
                    "stream": False
                }
                self.add_message("System", f"Loading {model_name} into memory... this may take a moment.")
                response = requests.post("http://localhost:11434/api/generate", headers=headers, json=data)
                if response.status_code == 200:
                    self.update_status(f"Model {model_name} loaded successfully")
                    self.add_message("System", f"{model_name} is now ready to use")
                else:
                    self.update_status(f"Error loading model: {response.text}")
                    self.add_message("System", f"Failed to load {model_name}: {response.text}")
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
                self.add_message("System", f"Error loading model: {str(e)}")

        threading.Thread(target=load, daemon=True).start()

    def unload_model(self):
        model_name = self.current_model
        if not model_name:
            self.add_message("System", "Please select a model to unload")
            return

        self.update_status(f"Unloading {model_name} from memory...")

        def unload():
            try:
                process = subprocess.Popen(
                    ["ollama", "stop", model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    universal_newlines=True
                )
                process.wait()
                if process.returncode == 0:
                    self.update_status(f"Model {model_name} unloaded from memory")
                    self.add_message("System", f"Successfully unloaded {model_name} from memory")
                else:
                    stdout_output = process.stdout.read() if hasattr(process.stdout, 'read') else ""
                    stderr_output = process.stderr.read() if hasattr(process.stderr, 'read') else ""
                    error_output = stderr_output or stdout_output or "Unknown error"
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

        confirmation_window = ctk.CTkToplevel(self.window)
        confirmation_window.title("Confirm Removal")
        confirmation_window.geometry("400x150")
        confirmation_window.transient(self.window)
        confirmation_window.grab_set()

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
            fg_color="#2196F3",
            hover_color="#1976D2",
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
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    universal_newlines=True
                )
                process.wait()
                if process.returncode == 0:
                    self.update_status("Model removed successfully!")
                    self.add_message("System", f"Successfully removed {model_name}")
                    self.window.after(0, self.refresh_models)
                else:
                    stdout_output = process.stdout.read() if hasattr(process.stdout, 'read') else ""
                    stderr_output = process.stderr.read() if hasattr(process.stderr, 'read') else ""
                    error_output = stderr_output or stdout_output or "Unknown error"
                    self.update_status("Failed to remove model!")
                    self.add_message("System", f"Failed to remove {model_name}: {error_output}")
            except Exception as e:
                self.update_status("Removal failed!")
                self.add_message("System", f"Error removing model: {str(e)}")

        threading.Thread(target=remove, daemon=True).start()

    def show_progress_frame(self):
        def update():
            self.progress_frame.grid()
            self.progress_bar.set(0)
            self.progress_label.configure(text="Starting download...")
        self.window.after(0, update)

    def hide_progress_frame(self):
        def update():
            self.progress_frame.grid_remove()
        self.window.after(0, update)

    def update_progress(self, progress, text):
        def update():
            self.progress_bar.set(progress)
            self.progress_label.configure(text=text)
        self.window.after(0, update)

    def parse_progress(self, line):
        try:
            if any(x in line.lower() for x in ["pulling", "initializing", "preparing", "reading", "computing", "writing"]):
                return 0.03

            progress_match = re.search(r'(\d+\.\d+)%', line)
            if progress_match:
                progress_percent = float(progress_match.group(1)) / 100
                return progress_percent

            mb_match = re.search(r'(\d+)(?:\.\d+)?MB/(\d+)(?:\.\d+)?MB', line)
            if mb_match:
                current_mb = float(mb_match.group(1))
                total_mb = float(mb_match.group(2))
                if total_mb > 0:
                    return current_mb / total_mb

            layer_match = re.search(r'layer: (\d+)/(\d+)', line)
            if layer_match:
                current_layer = int(layer_match.group(1))
                total_layers = int(layer_match.group(2))
                if total_layers > 0:
                    return current_layer / total_layers

            if "downloading" in line.lower():
                return 0.05

            return None
        except Exception as e:
            print(f"Error parsing progress: {e}")
            return None

    def download_model(self):
        model_name = self.model_entry.get().strip()
        if not model_name:
            self.add_message("System", "Please enter a model name")
            return

        self.update_status(f"Downloading {model_name}...")
        self.show_progress_frame()

        def disable_download():
            self.download_button.configure(state="disabled", text="Downloading...")
            self.model_entry.configure(state="disabled")
        self.window.after(0, disable_download)

        def download():
            try:
                self.update_progress(0.05, "Starting download...")
                download_successful = self.download_model_via_api(model_name)

                if not download_successful:
                    self.add_message("System", "API download failed. Falling back to CLI method...")
                    download_successful = self.download_model_via_cli(model_name)

                if download_successful:
                    self.update_status("Download complete!")
                    self.update_progress(1.0, f"Download complete: {model_name}")
                    self.add_message("System", f"Successfully downloaded {model_name}")
                    self.refresh_models()
                else:
                    self.update_status("Download failed!")
                    self.update_progress(0.1, "Download failed")
                    self.add_message("System", f"Failed to download {model_name}. Please check the model name and try again.")

                self.window.after(2000, self.hide_progress_frame)
            except Exception as e:
                self.update_status("Download failed!")
                self.update_progress(0, "Error during download")
                self.add_message("System", f"Error downloading model: {str(e)}")
                self.window.after(2000, self.hide_progress_frame)
            finally:
                def enable_download():
                    self.download_button.configure(state="normal", text="Download")
                    self.model_entry.configure(state="normal")
                self.window.after(0, enable_download)

        threading.Thread(target=download, daemon=True).start()

    def download_model_via_api(self, model_name):
        try:
            url = "http://localhost:11434/api/pull"
            payload = {"name": model_name, "stream": False}
            headers = {"Content-Type": "application/json"}

            with requests.post(url, json=payload, headers=headers, stream=True) as response:
                if response.status_code != 200:
                    error_text = response.text
                    self.add_message("System", f"API Error: {error_text}")
                    return False

                accumulated_data = ""
                current_progress = 0.05
                last_progress_update = time.time()

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if "status" in data:
                                status_msg = data["status"]
                                self.update_status(f"Status: {status_msg}")

                            if "completed" in data and "total" in data:
                                completed = data["completed"]
                                total = data["total"]
                                if total > 0:
                                    progress = completed / total
                                    if time.time() - last_progress_update > 0.5:
                                        self.update_progress(progress, f"Downloading {model_name}: {int(progress * 100)}%")
                                        last_progress_update = time.time()
                                    current_progress = progress

                            if "status" in data:
                                status = data["status"].lower()
                                if "downloading" in status and current_progress < 0.1:
                                    current_progress = 0.1
                                    self.update_progress(current_progress, f"Downloading {model_name}...")
                                elif "verifying" in status or "validating" in status and current_progress < 0.7:
                                    current_progress = 0.7
                                    self.update_progress(current_progress, f"Verifying {model_name}...")
                                elif "extracting" in status or "unpacking" in status and current_progress < 0.8:
                                    current_progress = 0.8
                                    self.update_progress(current_progress, f"Extracting {model_name}...")
                                elif "writing" in status or "finalizing" in status and current_progress < 0.9:
                                    current_progress = 0.9
                                    self.update_progress(current_progress, f"Finalizing {model_name}...")

                            if "done" in data.get("status", "").lower():
                                self.update_progress(1.0, f"Download complete: {model_name}")
                                return True

                            if "error" in data:
                                error_msg = data["error"]
                                self.add_message("System", f"Download error: {error_msg}")
                                return False

                        except json.JSONDecodeError as je:
                            accumulated_data += line.decode('utf-8')

                if current_progress > 0.5:
                    return True
                else:
                    if accumulated_data:
                        self.add_message("System", f"Incomplete download: {accumulated_data}")
                    return False

        except requests.RequestException as e:
            self.add_message("System", f"API request error: {str(e)}")
            return False
        except json.JSONDecodeError as je:
            self.add_message("System", f"Error parsing API response: {str(je)}")
            return False
        except Exception as e:
            self.add_message("System", f"API download error: {str(e)}")
            return False

    def download_model_via_cli(self, model_name):
        """Improved CLI download method with robust cancellation and progress"""
        try:
            self.download_process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True
            )

            start_time = time.time()
            max_time_without_output = 60
            last_output_time = start_time
            current_progress = 0.05
            download_output = []
            progress_update_time = time.time()

            def read_stream(stream, output_list, is_stderr=False):
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    clean_line = self.remove_ansi_escape_sequences(line.strip())
                    if clean_line:
                        output_list.append(clean_line)
                        if is_stderr:
                            self.add_message("System", f"Error: {clean_line}")
                        else:
                            if time.time() - progress_update_time > 0.5:
                                self.window.after(0, lambda cl=clean_line: self.update_status(f"Downloading: {cl}"))
                                progress_update_time = time.time()

            stdout_lines = []
            stderr_lines = []

            stdout_thread = threading.Thread(target=read_stream, args=(self.download_process.stdout, stdout_lines), daemon=True)
            stderr_thread = threading.Thread(target=read_stream, args=(self.download_process.stderr, stderr_lines, True), daemon=True)

            stdout_thread.start()
            stderr_thread.start()

            while self.download_process.poll() is None:
                if self.download_cancel_requested:
                    try:
                        self.download_process.terminate()
                        self.download_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.download_process.kill()
                    return False

                if time.time() - last_output_time > max_time_without_output:
                    self.add_message("System", "Download seems stuck. Terminating process.")
                    self.download_process.kill()
                    return False

                # Pulse progress bar even without new output
                if time.time() - progress_update_time > 1.0:
                    pulse_progress = min(0.9, current_progress + 0.05)
                    self.update_progress(pulse_progress, f"Downloading {model_name}...")
                    current_progress = pulse_progress
                    progress_update_time = time.time()

                time.sleep(0.2)

            stdout_thread.join()
            stderr_thread.join()

            full_output = "\n".join(stdout_lines + stderr_lines).lower()
            success_indicators = ["downloaded", "complete", "finished", "success"]
            for indicator in success_indicators:
                if indicator in full_output:
                    return True

            if stdout_lines or stderr_lines:
                return True

            return False

        except Exception as e:
            self.add_message("System", f"CLI download error: {str(e)}")
            return False
        finally:
            self.download_cancel_requested = False

    def remove_ansi_escape_sequences(self, text):
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
            elif sys.platform == "darwin":
                path = "/usr/local/share/ollama/models"
            elif sys.platform == "win32":
                path = r"C:\ProgramData\ollama\models"

            if os.path.exists(path):
                total_size = sum(os.path.getsize(os.path.join(path, f))
                                 for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)))
                size_gb = total_size / (1024 ** 3)
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
            self.check_disk_usage()
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.add_message("System", f"Error initializing chatbot: {str(e)}")

    def download_model_with_name(self, model_name):
        try:
            self.show_progress_frame()
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True
            )

            download_output = []
            last_progress_time = time.time()
            last_update_time = time.time()
            progress_seen = False

            for line in process.stdout:
                clean_line = ''.join(c for c in line if c.isprintable() and c not in '\r\x1b')
                clean_line = self.remove_ansi_escape_sequences(clean_line)
                if clean_line.strip():
                    download_output.append(clean_line.strip())
                    progress = self.parse_progress(clean_line)
                    if progress is not None:
                        progress_seen = True
                        self.update_progress(progress, f"Downloading {model_name}: {int(progress * 100)}%")
                        last_progress_time = time.time()
                    if time.time() - last_update_time > 0.5:
                        self.update_status(f"Downloading: {clean_line.strip()}")
                        last_update_time = time.time()
                    if not progress_seen and time.time() - last_progress_time > 3:
                        pulse_progress = (time.time() % 0.6) / 0.6 * 0.1 + 0.05
                        self.update_progress(pulse_progress, f"Downloading {model_name}...")
                        last_progress_time = time.time()

            process.wait()
            self.hide_progress_frame()

            if process.returncode == 0:
                self.update_status(f"Model {model_name} downloaded successfully")
                self.add_message("System", f"Successfully downloaded {model_name}")
                return True
            else:
                stderr_output = process.stderr.read() if hasattr(process.stderr, 'read') else ""
                error_output = stderr_output if stderr_output else "\n".join(download_output)
                self.update_status(f"Download failed: {error_output}")
                self.add_message("System", f"Error downloading {model_name}: {error_output}")
                print(f"Ollama pull error (code {process.returncode}): {error_output}")
                return False
        except Exception as e:
            self.update_status(f"Error downloading model: {str(e)}")
            self.add_message("System", f"Exception during download: {str(e)}")
            print(f"Exception during model download: {str(e)}")
            self.hide_progress_frame()
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
            self.chat_display.insert("end", f"[{timestamp}] {sender}: {message}\n")
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
        try:
            self.update_status("Shutting down Ollama...")
            stop_ollama = messagebox.askyesno("Exit", "Stop Ollama server when closing?") if messagebox_available else True
            if stop_ollama:
                if self.available_models:
                    for model in self.available_models:
                        try:
                            subprocess.run(["ollama", "stop", model],
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,
                                           timeout=2)
                        except:
                            pass
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
            self.window.destroy()

    def cancel_download(self):
        if self.download_process:
            self.download_cancel_requested = True
            self.update_status("Canceling download...")
            self.add_message("System", "Download canceled by user.")

            try:
                # First attempt to terminate gracefully
                self.download_process.terminate()
                # Wait for termination with timeout
                self.download_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't respond
                self.download_process.kill()
                self.add_message("System", "Process forcefully killed.")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ChatbotGUI()
    app.run()