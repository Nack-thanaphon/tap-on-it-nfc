import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import nfc_service
import threading
import time
from datetime import datetime
import api_service

class NFCApp:
    """Unified NFC application with read and write modes in a single window."""

    def __init__(self, root):
        self.root = root
        self.root.title("NFC Tag Management System")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f2f5")
        self.nfc_reader = nfc_service.NFCReader(self.log)
        self.current_mode = None  # 'read' or 'write'
        self.tasks = []
        self.read_mode_running = False
        self.last_uid = None

        # Initialize API service
        self.api = api_service.APIService()

        # Create frames for different modes
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.read_frame = ttk.Frame(self.root)
        self.write_frame = ttk.Frame(self.root)

        # Create variables for search and filter
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="All")
        self.date_filter_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        self.setup_ui()
        self.connect_reader()

    def setup_ui(self):
        # Configure styles
        style = ttk.Style()
        style.configure("Mode.TButton", font=("Arial", 12, "bold"), padding=10)
        style.configure("Back.TButton", font=("Arial", 10), padding=5)
        style.configure("Accent.TButton", font=("Arial", 10, "bold"), padding=8, background="#ff5555")

        # Set up the main selection screen
        self.setup_main_screen()

        # Set up the read mode screen
        self.setup_read_screen()

        # Set up the write mode screen
        self.setup_write_screen()

        # Start with the main screen
        self.show_main_screen()

    def setup_main_screen(self):
        """Set up the main selection screen."""
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(
            self.main_frame, text="NFC Tag Management", font=("Arial", 18, "bold")
        ).pack(pady=(0, 20))

        # Description
        ttk.Label(
            self.main_frame, text="Select an operation mode:", font=("Arial", 12)
        ).pack(pady=(0, 30))

        # Buttons frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X)

        # Read mode button
        read_button = ttk.Button(
            button_frame,
            text="Read Mode",
            style="Mode.TButton",
            command=self.show_read_mode,
        )
        read_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        # Write mode button
        write_button = ttk.Button(
            button_frame,
            text="Write Mode",
            style="Mode.TButton",
            command=self.show_write_mode,
        )
        write_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def setup_read_screen(self):
        """Set up the read mode screen."""
        # Back button at the top
        back_frame = ttk.Frame(self.read_frame)
        back_frame.pack(fill=tk.X, pady=(10, 20))

        ttk.Button(
            back_frame,
            text="← Back to Main",
            style="Back.TButton",
            command=self.show_main_screen,
        ).pack(side=tk.LEFT, padx=10)

        # Title
        ttk.Label(
            self.read_frame, text="NFC Read Mode", font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))

        # Status display
        status_frame = ttk.Frame(self.read_frame)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        ttk.Label(
            status_frame, text="Place NFC tag on reader...", font=("Arial", 12)
        ).pack(pady=10)

        # Data display frame
        data_frame = ttk.LabelFrame(self.read_frame, text="Tag Data")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # UID display
        uid_frame = ttk.Frame(data_frame)
        uid_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(uid_frame, text="UID:", width=10).pack(side=tk.LEFT)
        self.uid_var = tk.StringVar(value="None")
        ttk.Label(
            uid_frame, textvariable=self.uid_var, font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)

        # URL display
        url_frame = ttk.Frame(data_frame)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(url_frame, text="URL:", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value="None")
        ttk.Label(
            url_frame, textvariable=self.url_var, font=("Arial", 30, "bold")
        ).pack(side=tk.LEFT)
        
        # Action buttons frame
        action_frame = ttk.Frame(data_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Format Card button
        format_button = ttk.Button(
            action_frame,
            text="Format Card",
            command=self.format_card,
            style="Accent.TButton"
        )
        format_button.pack(side=tk.LEFT, padx=5)

        # Log display
        log_frame = ttk.LabelFrame(self.read_frame, text="Log")
        log_frame.pack(fill=tk.X, padx=20, pady=10)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_write_screen(self):
        """Set up the write mode screen with dashboard."""
        # Back button at the top
        back_frame = ttk.Frame(self.write_frame)
        back_frame.pack(fill=tk.X, pady=(10, 20))

        ttk.Button(
            back_frame,
            text="← Back to Main",
            style="Back.TButton",
            command=self.show_main_screen,
        ).pack(side=tk.LEFT, padx=10)

        # Dashboard content
        content_frame = ttk.Frame(self.write_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Header
        header = ttk.Frame(content_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="NFC Order Management", font=("Arial", 16, "bold")).pack(
            side=tk.LEFT
        )
        self.task_count_var = tk.StringVar(value="Orders for Today: 0")
        ttk.Label(header, textvariable=self.task_count_var, font=("Arial", 12)).pack(
            side=tk.RIGHT, padx=10
        )

        # Search and filter bar
        filter_frame = ttk.LabelFrame(content_frame, text="Search & Filter")
        filter_frame.pack(fill=tk.X, pady=5)

        # Create a 2x3 grid for search and filter controls
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill=tk.X, padx=10, pady=10)

        # Row 1
        # Search
        ttk.Label(filter_grid, text="Search:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        search_entry = ttk.Entry(filter_grid, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Status filter
        ttk.Label(filter_grid, text="Status:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        status_combo = ttk.Combobox(
            filter_grid, textvariable=self.status_filter_var, width=15
        )
        status_combo["values"] = (
            "All",
            "Pending",
            "In Progress",
            "Completed",
            "Success",
        )
        status_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        # Date filter
        ttk.Label(filter_grid, text="Date:").grid(
            row=0, column=4, sticky=tk.W, padx=5, pady=5
        )
        date_entry = ttk.Entry(filter_grid, textvariable=self.date_filter_var, width=12)
        date_entry.grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)

        # Row 2 - Buttons
        button_frame = ttk.Frame(filter_grid)
        button_frame.grid(row=1, column=0, columnspan=6, pady=5)

        ttk.Button(button_frame, text="Apply Filters", command=self.apply_filters).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Reset Filters", command=self.reset_filters).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Refresh Data", command=self.fetch_tasks).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Add New Order", command=self.add_task).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            button_frame, text="Disable Beep", command=self.nfc_reader.disable_beep
        ).pack(side=tk.LEFT, padx=5)

        # Task list
        task_frame = ttk.LabelFrame(content_frame, text="Today's Orders")
        task_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create scrollbars
        y_scrollbar = ttk.Scrollbar(task_frame, orient="vertical")
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(task_frame, orient="horizontal")
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Create treeview with scrollbars
        self.task_tree = ttk.Treeview(
            task_frame,
            columns=(
                "ID",
                "Order",
                "Customer",
                "Product",
                "URL",
                "Tag Color",
                "Status",
            ),
            show="headings",
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        # Configure scrollbars
        y_scrollbar.config(command=self.task_tree.yview)
        x_scrollbar.config(command=self.task_tree.xview)

        # Configure headings
        self.task_tree.heading("ID", text="ID")
        self.task_tree.heading("Order", text="Order #")
        self.task_tree.heading("Customer", text="Customer")
        self.task_tree.heading("Product", text="Product")
        self.task_tree.heading("URL", text="URL")
        self.task_tree.heading("Tag Color", text="Color")
        self.task_tree.heading("Status", text="Status")

        # Configure columns
        self.task_tree.column("ID", width=40, minwidth=40)
        self.task_tree.column("Order", width=80, minwidth=80)
        self.task_tree.column("Customer", width=120, minwidth=100)
        self.task_tree.column("Product", width=150, minwidth=100)
        self.task_tree.column("URL", width=200, minwidth=150)
        self.task_tree.column("Tag Color", width=60, minwidth=60)
        self.task_tree.column("Status", width=100, minwidth=80)

        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Context menu for tasks
        self.context_menu = tk.Menu(self.task_tree, tearoff=0)
        self.context_menu.add_command(label="Write URL", command=self.write_task_url)
        self.task_tree.bind("<Button-3>", self.show_context_menu)

        # Status area
        status_frame = ttk.LabelFrame(content_frame, text="Status Log")
        status_frame.pack(fill=tk.X, pady=10)
        self.status_text = scrolledtext.ScrolledText(status_frame, height=6)
        self.status_text.pack(padx=5, pady=5, fill=tk.BOTH)

    def connect_reader(self):
        """Connect to the NFC reader in a background thread."""

        def connect_loop():
            max_attempts = 5
            for attempt in range(max_attempts):
                if self.nfc_reader.connect():
                    self.nfc_reader.disable_beep()
                    self.log("NFC reader connected successfully.")
                    return
                self.log(
                    f"Connection attempt {attempt + 1}/{max_attempts} failed. Retrying in 3 seconds..."
                )
                time.sleep(3)
            self.log("Failed to connect to NFC reader.")
            messagebox.showerror("Error", "Could not connect to NFC reader.")

        threading.Thread(target=connect_loop, daemon=True).start()

    def show_main_screen(self):
        """Show the main selection screen."""
        # Stop any running read mode
        self.read_mode_running = False

        # Hide other frames
        self.read_frame.pack_forget()
        self.write_frame.pack_forget()

        # Show main frame
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.current_mode = None

    def show_read_mode(self):
        """Show the read mode screen."""
        # Hide other frames
        self.main_frame.pack_forget()
        self.write_frame.pack_forget()

        # Show read frame
        self.read_frame.pack(fill=tk.BOTH, expand=True)
        self.current_mode = "read"

        # Start tag polling
        self.read_mode_running = True
        threading.Thread(target=self.poll_tag, daemon=True).start()

    def show_write_mode(self):
        """Show the write mode screen."""
        # Hide other frames
        self.main_frame.pack_forget()
        self.read_frame.pack_forget()

        # Show write frame
        self.write_frame.pack(fill=tk.BOTH, expand=True)
        self.current_mode = "write"

        # Fetch and display tasks
        self.fetch_tasks()

    def poll_tag(self):
        """Poll for NFC tag in real-time."""
        card_removed_error_count = 0  # Counter for consecutive card removal errors
        last_error_time = 0  # Time of last error message
        connection_error_count = 0  # Counter for connection errors

        while self.read_mode_running:
            try:
                # Check if we need to attempt reconnection
                if connection_error_count > 5:
                    try:
                        self.log("Attempting to reconnect to reader...")
                        if self.nfc_reader.connect():
                            self.log("Successfully reconnected to reader")
                            connection_error_count = 0
                        else:
                            self.log("Failed to reconnect to reader, will retry later")
                            time.sleep(3)  # Wait before next attempt
                            continue
                    except Exception as reconnect_error:
                        self.log(f"Error during reconnection: {reconnect_error}")
                        time.sleep(3)  # Wait before next attempt
                        continue

                # Try to read the tag UID
                uid = None
                try:
                    uid = self.nfc_reader.read_uid()
                    # Reset connection error counter on successful operation
                    connection_error_count = 0
                except Exception as uid_error:
                    error_str = str(uid_error)
                    if "card not connected" in error_str.lower():
                        connection_error_count += 1
                        if connection_error_count % 5 == 1:  # Log only occasionally
                            self.log(
                                "Card reader connection issue, will attempt to recover"
                            )
                        time.sleep(1)
                        continue
                    else:
                        # For other errors, just continue with uid=None
                        pass

                if uid:
                    # Reset error counter when successful read
                    card_removed_error_count = 0

                    if uid != self.last_uid:
                        # New tag detected
                        self.last_uid = uid
                        self.uid_var.set(uid)

                        # Try to read URL safely
                        url = None
                        try:
                            url = self.nfc_reader.read_ntag_url()
                        except Exception as url_error:
                            self.log(f"Error reading URL: {url_error}")

                        self.url_var.set(url if url else "None")
                        self.log(
                            f"Tag detected - UID: {uid}, URL: {url if url else 'None'}"
                        )
                else:
                    # No tag present, clear the display if there was a tag before
                    if self.last_uid:
                        self.last_uid = None
                        self.uid_var.set("None")
                        self.url_var.set("None")
                        self.log("Tag removed")

                # Successful operation, reset error counter
                card_removed_error_count = 0
                time.sleep(0.5)

            except Exception as e:
                # Check if the error is due to card removal or connection issues
                error_str = str(e)
                current_time = time.time()

                if "card not connected" in error_str.lower():
                    # Card reader connection error
                    connection_error_count += 1
                    if connection_error_count % 5 == 1:  # Log only occasionally
                        self.log(
                            "Card reader connection issue, will attempt to recover"
                        )
                    time.sleep(1)
                elif (
                    "0x80100069" in error_str
                    or "card has been removed" in error_str.lower()
                ):
                    # Card removal error
                    card_removed_error_count += 1

                    # Only log the first error or if it's been a while since the last one
                    if (
                        card_removed_error_count == 1
                        or (current_time - last_error_time) > 5
                    ):
                        if self.last_uid:
                            self.last_uid = None
                            self.uid_var.set("None")
                            self.url_var.set("None")
                            self.log("Tag removed")
                        last_error_time = current_time

                    # Adjust polling frequency based on consecutive errors
                    if card_removed_error_count > 5:
                        time.sleep(2)  # Longer delay after multiple errors
                    else:
                        time.sleep(0.5)
                else:
                    # Other error - always log these but not too frequently
                    if (current_time - last_error_time) > 3:
                        self.log(f"Error polling tag: {e}")
                        last_error_time = current_time
                    time.sleep(1)

    def log(self, message):
        """Log a message to the appropriate text widget."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # Log to console for debugging
        print(f"[NFC App] {message}")

        # Log to the appropriate text widget based on current mode
        if self.current_mode == "read":
            self.log_text.insert(tk.END, log_message)
            self.log_text.see(tk.END)
        elif self.current_mode == "write":
            self.status_text.insert(tk.END, log_message)
            self.status_text.see(tk.END)

    def show_context_menu(self, event):
        """Show context menu for task tree."""
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def fetch_tasks(self):
        """Fetch tasks from the database with current filters applied."""
        # Get filter values
        search_term = (
            self.search_var.get().strip() if self.search_var.get().strip() else None
        )
        status = (
            self.status_filter_var.get()
            if self.status_filter_var.get() != "All"
            else None
        )
        date = self.date_filter_var.get()

        # Fetch tasks from API
        self.tasks = self.api.get_orders(
            date=date, status=status, search_term=search_term
        )

        # Update count label
        self.task_count_var.set(f"Orders for Today: {len(self.tasks)}")

        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        # Add tasks to treeview
        for task in self.tasks:
            # Insert into treeview
            self.task_tree.insert(
                "",
                tk.END,
                values=(
                    task["id"],
                    task["order_number"],
                    task["customer_name"],
                    task["title"],  # product_name stored as title
                    task["url"],
                    task["tag_color"],
                    task.get("status", ""),
                ),
            )

            # Configure tag color
            self.task_tree.tag_configure(
                f"color_{task['id']}", background=task["tag_color"]
            )

            # Configure status-based styling
            if task.get("status") in ["Success", "Completed"]:
                self.task_tree.tag_configure(
                    f"success_{task['id']}",
                    foreground="green",
                    font=("Arial", 9, "bold"),
                )
                self.task_tree.item(
                    self.task_tree.get_children()[-1],
                    tags=(
                        f"color_{task['id']}",
                        f"success_{task['id']}",
                    ),
                )
            elif task.get("status") == "In Progress":
                self.task_tree.tag_configure(
                    f"progress_{task['id']}",
                    foreground="blue",
                    font=("Arial", 9, "bold"),
                )
                self.task_tree.item(
                    self.task_tree.get_children()[-1],
                    tags=(
                        f"color_{task['id']}",
                        f"progress_{task['id']}",
                    ),
                )
            else:
                self.task_tree.item(
                    self.task_tree.get_children()[-1], tags=(f"color_{task['id']}",)
                )

    def add_task(self):
        """Add a new order via modal."""
        modal = tk.Toplevel(self.root)
        modal.title("Add New Order")
        modal.geometry("500x400")
        modal.transient(self.root)
        modal.grab_set()

        ttk.Label(modal, text="Add New Order", font=("Arial", 14, "bold")).pack(pady=10)

        # Create a frame for the form
        form_frame = ttk.Frame(modal, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Order Number
        ttk.Label(form_frame, text="Order Number:").grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        order_entry = ttk.Entry(form_frame, width=30)
        order_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Generate a default order number
        today = datetime.now().strftime("%Y%m%d")
        order_entry.insert(0, f"ORD-{today}-{len(self.tasks) + 1:03d}")

        # Customer Name
        ttk.Label(form_frame, text="Customer Name:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        customer_entry = ttk.Entry(form_frame, width=30)
        customer_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        # Product Name
        ttk.Label(form_frame, text="Product Name:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        product_entry = ttk.Entry(form_frame, width=30)
        product_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

        # URL
        ttk.Label(form_frame, text="URL:").grid(row=3, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(form_frame, width=40)
        url_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        url_entry.insert(0, "https://")

        # Tag Color
        ttk.Label(form_frame, text="Tag Color:").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        color_var = tk.StringVar(value="#FF5733")
        color_options = {
            "Red": "#FF5733",
            "Green": "#33FF57",
            "Blue": "#3357FF",
            "Pink": "#FF33A1",
            "Orange": "#FFA500",
            "Purple": "#800080",
        }
        color_menu = ttk.OptionMenu(
            form_frame, color_var, "#FF5733", *color_options.values()
        )
        color_menu.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)

        # Status
        ttk.Label(form_frame, text="Status:").grid(row=5, column=0, sticky=tk.W, pady=5)
        status_var = tk.StringVar(value="Pending")
        status_combo = ttk.Combobox(form_frame, textvariable=status_var, width=15)
        status_combo["values"] = ("Pending", "In Progress", "Completed")
        status_combo.grid(row=5, column=1, sticky=tk.W, pady=5, padx=5)

        # Buttons
        button_frame = ttk.Frame(modal)
        button_frame.pack(pady=15)

        def save_task():
            order_number = order_entry.get().strip()
            customer_name = customer_entry.get().strip()
            product_name = product_entry.get().strip()
            url = url_entry.get().strip()

            # Validate inputs
            if not order_number or not customer_name or not product_name or not url:
                messagebox.showerror("Error", "All fields are required!", parent=modal)
                return

            if not url.startswith(("http://", "https://")):
                url = "http://" + url

            # Add via API
            new_id = self.api.add_order(
                order_number=order_number,
                customer_name=customer_name,
                product_name=product_name,
                url=url,
                tag_color=color_var.get(),
                status=status_var.get(),
            )

            if new_id:
                messagebox.showinfo(
                    "Success", "New order added successfully!", parent=modal
                )
                self.fetch_tasks()  # Refresh task list
                modal.destroy()
            else:
                messagebox.showerror("Error", "Failed to add new order", parent=modal)

        ttk.Button(button_frame, text="Save", command=save_task).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(button_frame, text="Cancel", command=modal.destroy).pack(
            side=tk.LEFT, padx=10
        )

    def write_task_url(self):
        """Write selected task's URL to NFC tag."""
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a task!")
            return

        task_id = self.task_tree.item(selected[0])["values"][0]
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            messagebox.showerror("Error", "Task not found!")
            return

        # Create a modal dialog for the write operation
        write_dialog = tk.Toplevel(self.root)
        write_dialog.title("Write NFC Tag")
        write_dialog.geometry("400x250")
        write_dialog.transient(self.root)
        write_dialog.grab_set()
        write_dialog.resizable(False, False)

        # Center the dialog
        write_dialog.update_idletasks()
        width = write_dialog.winfo_width()
        height = write_dialog.winfo_height()
        x = (write_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (write_dialog.winfo_screenheight() // 2) - (height // 2)
        write_dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Dialog content
        ttk.Label(
            write_dialog, text="Write URL to NFC Tag", font=("Arial", 14, "bold")
        ).pack(pady=(15, 10))

        ttk.Label(write_dialog, text=f"Task: {task['title']}", font=("Arial", 11)).pack(
            pady=2
        )

        ttk.Label(write_dialog, text=f"URL: {task['url']}", font=("Arial", 11)).pack(
            pady=(2, 15)
        )

        instruction_label = ttk.Label(
            write_dialog,
            text="Place NFC tag on reader and hold it steady...",
            font=("Arial", 11),
        )
        instruction_label.pack(pady=5)

        status_var = tk.StringVar(value="Waiting for tag...")
        status_label = ttk.Label(
            write_dialog, textvariable=status_var, font=("Arial", 11, "bold")
        )
        status_label.pack(pady=10)

        # Progress bar
        progress = ttk.Progressbar(write_dialog, mode="indeterminate")
        progress.pack(fill=tk.X, padx=50, pady=5)
        progress.start(10)  # Start the progress bar immediately

        # Buttons frame
        button_frame = ttk.Frame(write_dialog)
        button_frame.pack(fill=tk.X, pady=15)

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=write_dialog.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=10)

        # Variables for tag detection
        tag_detected = False
        tag_uid = None
        polling_active = True

        def poll_for_tag():
            """Poll for NFC tag and automatically start writing when detected."""
            nonlocal tag_detected, tag_uid, polling_active

            if not polling_active:
                return

            try:
                current_uid = self.nfc_reader.read_uid()
                if current_uid and not tag_detected:
                    # Tag detected, start writing
                    tag_detected = True
                    tag_uid = current_uid

                    # Update UI
                    status_var.set(f"Tag detected (UID: {current_uid[:8]}...)")
                    instruction_label.configure(
                        text="Writing to tag. Keep it steady..."
                    )

                    # Log the operation
                    self.log(
                        f"Writing URL: {task['url']} to tag with UID: {current_uid}"
                    )

                    # Start the write operation in a separate thread
                    threading.Thread(target=perform_write, daemon=True).start()
                    return

                # If no tag detected or still waiting for write to complete
                if not tag_detected:
                    write_dialog.after(100, poll_for_tag)  # Continue polling
            except Exception as e:
                if polling_active:
                    self.log(f"Error polling for tag: {e}")
                    write_dialog.after(500, poll_for_tag)  # Retry after a delay

        def perform_write():
            """Perform the actual write operation."""
            nonlocal polling_active

            try:
                # Attempt to write the URL to the tag
                if self.nfc_reader.write_ntag_url(task["url"]):
                    # Success
                    polling_active = False
                    self.root.after(0, lambda: handle_write_result(True))
                    self.log(
                        f"Successfully wrote URL: {task['url']} for task {task['title']}"
                    )
                else:
                    # Failed for some reason
                    polling_active = False
                    self.root.after(
                        0,
                        lambda: handle_write_result(
                            False, "Failed to write to tag. Please try again."
                        ),
                    )
                    self.log(f"Failed to write URL: {task['url']}")
            except Exception as e:
                # Handle specific exceptions
                polling_active = False
                error_msg = str(e)
                if "0x80100069" in error_msg:
                    error_msg = "Tag was removed during writing. Please keep it steady on the reader."
                elif "0x80100066" in error_msg:
                    error_msg = "No tag detected. Please place a tag on the reader."
                else:
                    error_msg = f"Error writing to tag: {error_msg}"

                self.log(f"Error: {error_msg}")
                self.root.after(0, lambda: handle_write_result(False, error_msg))

        def handle_write_result(success, error_msg=None):
            """Handle the result of the write operation."""
            nonlocal polling_active, tag_detected

            if success:
                progress.stop()
                status_var.set("Success! URL written to tag")
                instruction_label.configure(text="Tag has been successfully programmed")

                # Update task status in the list
                self.update_task_status(task["id"], "Success")

                # Auto-close after success
                write_dialog.after(2000, write_dialog.destroy)
            else:
                progress.stop()
                status_var.set(error_msg)
                instruction_label.configure(text="Please try again with a new tag")

                # Reset for a new attempt
                tag_detected = False
                polling_active = True

                # Start polling again after a delay
                write_dialog.after(1500, poll_for_tag)

        # Handle dialog close
        def on_dialog_close():
            nonlocal polling_active
            polling_active = False
            write_dialog.destroy()

        write_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        # Start polling for tags immediately
        poll_for_tag()

    def update_task_status(self, task_id, status):
        """Update the status of a task in the list and database."""
        # Update via API
        self.api.update_order_status(task_id, status)

        # Update the task in the tasks list
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = status
                break

        # Find the item in the treeview
        for item in self.task_tree.get_children():
            item_values = self.task_tree.item(item, "values")
            if item_values and int(item_values[0]) == task_id:
                # Update the status column (index 6 for the new structure)
                new_values = list(item_values)
                new_values[6] = status
                self.task_tree.item(item, values=new_values)

                # Apply appropriate styling
                current_tags = list(self.task_tree.item(item, "tags"))

                # Remove any existing status tags
                current_tags = [
                    tag
                    for tag in current_tags
                    if not (tag.startswith("success_") or tag.startswith("progress_"))
                ]

                # Add new status tag
                if status in ["Success", "Completed"]:
                    self.task_tree.tag_configure(
                        f"success_{task_id}",
                        foreground="green",
                        font=("Arial", 9, "bold"),
                    )
                    if f"success_{task_id}" not in current_tags:
                        current_tags.append(f"success_{task_id}")
                elif status == "In Progress":
                    self.task_tree.tag_configure(
                        f"progress_{task_id}",
                        foreground="blue",
                        font=("Arial", 9, "bold"),
                    )
                    if f"progress_{task_id}" not in current_tags:
                        current_tags.append(f"progress_{task_id}")

                self.task_tree.item(item, tags=current_tags)
                break

    def apply_filters(self):
        """Apply the current filters and refresh the task list."""
        self.fetch_tasks()

    def reset_filters(self):
        """Reset all filters to default values."""
        self.search_var.set("")
        self.status_filter_var.set("All")
        self.date_filter_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.fetch_tasks()

    def format_card(self):
        """Format/erase the current NFC tag."""
        if messagebox.askyesno("Format Card", "Are you sure you want to format this NFC tag? This will erase all data on the tag."):
            self.log("Starting card format operation...")
            
            # Check if a tag is present
            uid = self.nfc_reader.read_uid()
            if not uid:
                messagebox.showerror("Format Error", "No NFC tag detected. Please place a tag on the reader.")
                return
                
            # Attempt to format the card
            if self.nfc_reader.format_card():
                messagebox.showinfo("Format Complete", "The NFC tag has been successfully formatted.")
                
                # Update the display
                self.uid_var.set(uid)  # Keep showing the UID
                self.url_var.set("Empty (Formatted)")  # Show that the tag is now empty
                self.log(f"Successfully formatted tag with UID: {uid}")
            else:
                messagebox.showerror("Format Error", "Failed to format the NFC tag. Please try again.")
                self.log("Format operation failed.")
        else:
            self.log("Format operation cancelled.")


if __name__ == "__main__":
    root = tk.Tk()
    app = NFCApp(root)
    root.mainloop()
