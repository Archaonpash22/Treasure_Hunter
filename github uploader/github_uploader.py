import tkinter as tk
from tkinter import filedialog, messagebox
import git
import os

# --- Constants for Dark Mode ---
BG_COLOR = "#2E2E2E"
FG_COLOR = "#FFFFFF"
ENTRY_BG = "#3C3C3C"
ENTRY_FG = "#FFFFFF"
BUTTON_BG = "#555555"
BUTTON_FG = "#FFFFFF"
LABEL_FONT = ("Helvetica", 12)
ENTRY_FONT = ("Helvetica", 12)
BUTTON_FONT = ("Helvetica", 12, "bold")

class GitHubUploader(tk.Tk):
    """
    A simple GUI application to clone, stage, commit, and push changes to a Git repository.
    """
    def __init__(self):
        super().__init__()

        # --- Window Configuration ---
        self.title("GitHub Uploader")
        self.geometry("700x450") # Increased size for better layout
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        # --- Class Variables ---
        self.repo_url = tk.StringVar()
        self.local_path = tk.StringVar()
        self.repo = None

        # --- UI Widgets ---
        self.create_widgets()

        # --- Set Machine-Specific Defaults ---
        self.set_defaults()


    def set_defaults(self):
        """
        Checks the current user and sets a default GitHub repository URL and local path
        if it matches the specified user ('archa'). This makes the setting machine-specific.
        """
        try:
            if os.getlogin().lower() == 'archa':
                self.repo_url.set("https://github.com/Archaonpash22/Treasure_Hunter")
                # Set the default local path for the specified user
                default_local = r"C:\Users\archa\Desktop\Treasure_Hunter"
                if os.path.isdir(default_local):
                    self.local_path.set(default_local)
        except OSError:
            # os.getlogin() can fail in some environments. Ignore and don't set defaults.
            pass


    def create_widgets(self):
        """Creates and arranges all the UI widgets in the main window."""
        main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- GitHub Repository URL ---
        repo_url_frame = tk.Frame(main_frame, bg=BG_COLOR)
        repo_url_frame.pack(fill=tk.X, pady=(0, 15))
        repo_url_label = tk.Label(repo_url_frame, text="GitHub Repo URL (only for new clones):", bg=BG_COLOR, fg=FG_COLOR, font=LABEL_FONT)
        repo_url_label.pack(anchor="w")
        self.repo_url_entry = tk.Entry(repo_url_frame, textvariable=self.repo_url, font=ENTRY_FONT, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR, relief=tk.FLAT)
        self.repo_url_entry.pack(fill=tk.X, pady=(5,0))

        # --- Local Folder Selection ---
        local_path_frame = tk.Frame(main_frame, bg=BG_COLOR)
        local_path_frame.pack(fill=tk.X, pady=10)
        local_path_label = tk.Label(local_path_frame, text="Choose Local Folder:", bg=BG_COLOR, fg=FG_COLOR, font=LABEL_FONT)
        local_path_label.pack(anchor="w")
        
        local_entry_frame = tk.Frame(local_path_frame, bg=BG_COLOR)
        local_entry_frame.pack(fill=tk.X, pady=(5,0))
        self.local_path_entry = tk.Entry(local_entry_frame, textvariable=self.local_path, font=ENTRY_FONT, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR, relief=tk.FLAT)
        self.local_path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        browse_button = tk.Button(local_entry_frame, text="Browse", command=self.browse_local_folder, bg=BUTTON_BG, fg=BUTTON_FG, font=BUTTON_FONT, relief=tk.FLAT, padx=10)
        browse_button.pack(side=tk.LEFT, padx=(10, 0))

        # --- Commit Message ---
        commit_label = tk.Label(main_frame, text="Commit Message:", bg=BG_COLOR, fg=FG_COLOR, font=LABEL_FONT)
        commit_label.pack(anchor="w", pady=(20, 5))
        self.commit_entry = tk.Text(main_frame, height=5, font=ENTRY_FONT, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR, relief=tk.FLAT, wrap=tk.WORD)
        self.commit_entry.pack(fill=tk.X, expand=True)

        # --- Status Label ---
        self.status_label = tk.Label(main_frame, text="", bg=BG_COLOR, fg=FG_COLOR, font=("Helvetica", 10))
        self.status_label.pack(anchor="w", pady=(10, 0))

        # --- Upload Button ---
        upload_button = tk.Button(main_frame, text="Commit and Push to GitHub", command=self.upload_to_github, bg="#4CAF50", fg=FG_COLOR, font=BUTTON_FONT, relief=tk.FLAT, pady=10)
        upload_button.pack(fill=tk.X, pady=(20, 0))


    def browse_local_folder(self):
        """Opens a dialog to select a local folder."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.local_path.set(folder_selected)
            self.update_status(f"Local folder selected: {folder_selected}", "green")

    def upload_to_github(self):
        """Handles the logic for cloning, staging, committing, and pushing."""
        repo_url = self.repo_url.get().strip()
        local_path = self.local_path.get().strip()
        commit_message = self.commit_entry.get("1.0", tk.END).strip()

        # --- Input Validation ---
        if not local_path:
            messagebox.showerror("Error", "Please select a local folder.")
            return
        if not commit_message:
            messagebox.showerror("Error", "Please enter a commit message.")
            return

        try:
            # --- Initialize or Clone Repository ---
            # Case 1: The selected local path is already a Git repository.
            if os.path.isdir(os.path.join(local_path, '.git')):
                self.update_status("Existing repository found. Using its configuration.", "yellow")
                self.repo = git.Repo(local_path)
            
            # Case 2: The local path is not a repository, so we try to clone.
            else:
                if not repo_url:
                    messagebox.showerror("Error", "The selected folder is not a Git repository, and no GitHub URL was provided to clone from.")
                    self.update_status("Error: No repo URL for cloning.", "red")
                    return
                
                # We can only clone into an empty directory.
                if not os.path.exists(local_path) or not os.listdir(local_path):
                    self.update_status(f"Cloning from {repo_url}...", "orange")
                    try:
                        if not os.path.exists(local_path):
                            os.makedirs(local_path)
                        self.repo = git.Repo.clone_from(repo_url, local_path)
                        self.update_status("Clone successful.", "green")
                    except git.exc.GitCommandError as e:
                        messagebox.showerror("Clone Error", f"Could not clone repository: {e.stderr}")
                        self.update_status("Error: Cloning failed.", "red")
                        return
                else:
                    messagebox.showerror("Error", f"The folder '{local_path}' is not empty and is not a Git repository. Please choose an empty folder to clone into, or an existing repository.")
                    self.update_status("Error: Target folder not empty.", "red")
                    return

            # --- Check for changes ---
            if not self.repo.is_dirty(untracked_files=True):
                self.update_status("No changes to commit.", "yellow")
                messagebox.showinfo("Info", "There are no changes to commit.")
                return

            # --- Git Add ---
            self.update_status("Staging all changes (git add .)...", "orange")
            self.repo.git.add(A=True)

            # --- Git Commit ---
            self.update_status(f"Committing with message: '{commit_message}'...", "orange")
            self.repo.index.commit(commit_message)

            # --- Git Push ---
            self.update_status("Pushing to remote 'origin'...", "orange")
            # This uses the remote named 'origin' configured in the local repository itself.
            origin = self.repo.remote(name='origin')
            origin.push()

            self.update_status("Successfully pushed to GitHub!", "green")
            messagebox.showinfo("Success", "Your changes have been successfully uploaded to GitHub.")
            self.commit_entry.delete("1.0", tk.END)

        except git.exc.GitCommandError as e:
            error_message = f"Git Error: {e.stderr}"
            self.update_status(error_message, "red")
            messagebox.showerror("Git Error", error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            self.update_status(error_message, "red")
            messagebox.showerror("Error", error_message)

    def update_status(self, message, color):
        """Updates the status label with a given message and color."""
        self.status_label.config(text=message, fg=color)
        self.update_idletasks() # Force UI update

if __name__ == "__main__":
    # Before running, ensure you have GitPython installed:
    # pip install GitPython
    app = GitHubUploader()
    app.mainloop()
