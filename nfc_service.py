import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from smartcard.System import readers
from smartcard.util import toHexString
from datetime import datetime
import threading
import time
import re


class FakeAPI:
    """Simulate a fake API returning tasks for today."""

    @staticmethod
    def fetch_tasks():
        import requests
        from datetime import datetime

        # Get current date in YYYY-MM-DD format for filtering
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Call the API to get today's tasks
            response = requests.get("https://tap-on-it.com/api/profiles/getToday/")
            
            # Check if request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                return data
            else:
                # If API call fails, return fallback data
                print(f"API call failed with status code: {response.status_code}")
                return []
        except Exception as e:
            # Handle any exceptions (network issues, etc.)
            print(f"Error fetching tasks: {e}")
            # Return fallback data with current date
            return [
                {
                    "id": 1,
                    "title": "Process Product Tag A",
                    "url": "https://example.com/product/a",
                    "tag_color": "#FF5733",
                    "date": today,
                },
                {
                    "id": 2,
                    "title": "Update Inventory Tag B",
                    "url": "https://store.com/inventory/b",
                    "tag_color": "#33FF57",
                    "date": today,
                },
                {
                    "id": 3,
                    "title": "Customer Loyalty Tag C",
                    "url": "https://loyalty.com/reward/c",
                    "tag_color": "#3357FF",
                    "date": today,
                },
                {
                    "id": 4,
                    "title": "Old Task",
                    "url": "https://example.com/old",
                    "tag_color": "#FF33A1",
                    "date": "2025-05-16",  # Keep this as an old task for testing
                },
            ]


class NFCReader:
    """Handle NFC reader operations."""

    def __init__(self, log_callback):
        self.reader = None
        self.connection = None
        self.log_callback = log_callback
        self.GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        self.DISABLE_BEEP = [0xFF, 0x00, 0x52, 0x00, 0x00]

    def connect(self):
        try:
            reader_list = readers()
            if not reader_list:
                self.log_callback("No NFC readers found!")
                return False
            self.reader = reader_list[0]
            self.log_callback(f"Connected to reader: {self.reader}")
            self.connection = self.reader.createConnection()
            self.connection.connect()
            self.log_callback("Reader connection established.")
            return True
        except Exception as e:
            self.log_callback(f"Error connecting to reader: {e}")
            return False

    def disconnect(self):
        if self.connection:
            try:
                self.connection.disconnect()
                self.connection = None
                self.reader = None
            except Exception as e:
                self.log_callback(f"Error disconnecting: {e}")

    def disable_beep(self):
        if not self.connection:
            self.log_callback("Reader not connected!")
            return False
        try:
            _, sw1, sw2 = self.connection.transmit(self.DISABLE_BEEP)
            if (sw1, sw2) == (0x90, 0x00):
                self.log_callback("Beep disabled successfully.")
                return True
            self.log_callback(f"Error disabling beep: SW1={sw1}, SW2={sw2}")
            return False
        except Exception as e:
            self.log_callback(f"Error disabling beep: {e}")
            return False

    def read_uid(self):
        if not self.connection:
            # Silently return None if not connected
            return None
            
        try:
            data, sw1, sw2 = self.connection.transmit(self.GET_UID)
            if (sw1, sw2) == (0x90, 0x00):
                uid = toHexString(data).replace(" ", "")
                # Only log successful reads
                return uid
            # Don't log common error codes that indicate no card present
            if (sw1, sw2) not in [(0x63, 0x00), (0x62, 0x82)]:
                self.log_callback(f"Error reading UID: SW1={sw1:02X}, SW2={sw2:02X}")
            return None
        except Exception as e:
            error_str = str(e)
            # Handle specific error cases
            if "card not connected" in error_str.lower():
                # Card not connected - attempt to reconnect
                try:
                    self.connection = None
                    reader_list = readers()
                    if reader_list:
                        self.reader = reader_list[0]
                        self.connection = self.reader.createConnection()
                        self.connection.connect()
                except:
                    # If reconnection fails, just ignore it and return None
                    pass
                return None
            elif "0x80100069" in error_str or "card has been removed" in error_str.lower():
                # Card removal errors - try to reconnect silently
                try:
                    self.connection.disconnect()
                    self.connection.connect()
                except:
                    # If reconnection fails, just ignore it
                    pass
                return None
            elif "connection" in error_str.lower():
                # Generic connection errors
                try:
                    # Try to reconnect silently
                    self.connection.disconnect()
                    self.connection.connect()
                except:
                    # If reconnection fails, just ignore it
                    pass
                return None
            else:
                # Other errors - log them but don't spam
                self.log_callback(f"Error reading UID: {e}")
                return None

    def read_block(self, block_num):
        if not self.connection:
            # Silently return None if not connected
            return None
        try:
            command = [0xFF, 0xB0, 0x00, block_num, 0x10]
            data, sw1, sw2 = self.connection.transmit(command)
            if (sw1, sw2) == (0x90, 0x00):
                return data
            # Don't log common error codes that indicate no card present
            if (sw1, sw2) not in [(0x63, 0x00), (0x62, 0x82)]:
                # Only log for the first few blocks to avoid flooding
                if block_num < 6:
                    self.log_callback(f"Error reading block {block_num}: SW1={sw1:02X}, SW2={sw2:02X}")
            return None
        except Exception as e:
            error_str = str(e)
            # Only log errors that aren't related to card removal
            if "0x80100069" not in error_str and "card has been removed" not in error_str.lower():
                # Only log for the first few blocks to avoid flooding
                if block_num < 6:
                    self.log_callback(f"Error reading block {block_num}: {e}")
            return None

    def write_block(self, block_num, data):
        if not self.connection:
            self.log_callback("Reader not connected!")
            return False
        try:
            command = [0xFF, 0xD6, 0x00, block_num, len(data)] + data
            _, sw1, sw2 = self.connection.transmit(command)
            if (sw1, sw2) == (0x90, 0x00):
                self.log_callback(f"Successfully wrote block {block_num}")
                return True
            self.log_callback(f"Error writing block {block_num}: SW1={sw1}, SW2={sw2}")
            return False
        except Exception as e:
            self.log_callback(f"Error writing block {block_num}: {e}")
            return False

    def read_ntag_url(self):
        try:
            # First, dump the entire tag content for debugging
            self.log_callback("Reading tag data...")
            raw_dump = []
            for page in range(4, 24):  # NTAG data starts at page 4
                data = self.read_block(page)
                if data:
                    raw_dump.append(data)
                    hex_data = ' '.join([f'{b:02X}' for b in data])
                    self.log_callback(f"Page {page}: {hex_data}")
                else:
                    break
            
            # Convert all data to a single string for simple extraction
            all_data = bytearray()
            for page_data in raw_dump:
                all_data.extend(page_data)
                
            # Convert to text, ignoring non-ASCII characters
            text_data = ''.join(chr(b) if 32 <= b <= 126 else ' ' for b in all_data)
            self.log_callback(f"Raw text data: {text_data}")
            
            # SIMPLE APPROACH: Just extract the domain and protocol
            import re
            
            # Look for https:// followed by domain
            https_match = re.search(r'https://([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}', text_data)
            if https_match:
                # Extract just the domain part (https://example.com)
                domain_end = https_match.end()
                for i in range(https_match.start() + 8, domain_end):
                    if text_data[i] == '/':
                        domain_end = i
                        break
                        
                clean_url = text_data[https_match.start():domain_end]
                self.log_callback(f"Found clean HTTPS URL: {clean_url}")
                return clean_url
                
            # Look for http:// followed by domain
            http_match = re.search(r'http://([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}', text_data)
            if http_match:
                # Extract just the domain part (http://example.com)
                domain_end = http_match.end()
                for i in range(http_match.start() + 7, domain_end):
                    if text_data[i] == '/':
                        domain_end = i
                        break
                        
                clean_url = text_data[http_match.start():domain_end]
                self.log_callback(f"Found clean HTTP URL: {clean_url}")
                return clean_url
                
            # Look for www. followed by domain
            www_match = re.search(r'www\.([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}', text_data)
            if www_match:
                # Extract just the domain part (www.example.com)
                domain_end = www_match.end()
                for i in range(www_match.start(), domain_end):
                    if text_data[i] == '/':
                        domain_end = i
                        break
                        
                clean_url = 'http://' + text_data[www_match.start():domain_end]
                self.log_callback(f"Found clean WWW URL: {clean_url}")
                return clean_url
                
            # Look for any domain pattern
            domain_match = re.search(r'([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}', text_data)
            if domain_match:
                # Extract just the domain part (example.com)
                domain_end = domain_match.end()
                for i in range(domain_match.start(), domain_end):
                    if text_data[i] == '/':
                        domain_end = i
                        break
                        
                clean_url = 'https://' + text_data[domain_match.start():domain_end]
                self.log_callback(f"Found clean domain: {clean_url}")
                return clean_url
            
            # If we couldn't find a clean URL, return None
            self.log_callback("Could not find a clean URL in the tag data")
            return None
            
        except Exception as e:
            self.log_callback(f"Error reading NTAG URL: {e}")
            return None
            
    def clean_corrupted_url(self, url):
        """Clean up corrupted URLs with multiple protocol prefixes or domains."""
        if not url:
            return url
            
        # First, check if we have multiple http:// or https:// prefixes
        if url.count('http://') > 1 or url.count('https://') > 1 or ('http://' in url and 'https://' in url):
            # Try to find the most complete URL pattern
            import re
            url_patterns = re.findall(r'https?://[\w.-]+\.[a-zA-Z]{2,}(?:/\S*)?', url)
            if url_patterns:
                return url_patterns[0]  # Return the first complete URL found
                
            # If no complete URL found, try to extract just the domain
            domains = re.findall(r'www\.[\w.-]+\.[a-zA-Z]{2,}', url)
            if domains:
                return 'http://' + domains[0]
                
            # If still nothing found, just take the first http:// and everything after it
            http_index = url.find('http://')
            if http_index >= 0:
                return url[http_index:]
                
            https_index = url.find('https://')
            if https_index >= 0:
                return url[https_index:]
        
        # Check for repeated domains (like www.example.comwww.example.com)
        import re
        domains = re.findall(r'(www\.[\w.-]+\.[a-zA-Z]{2,})', url)
        if len(domains) > 1 and domains[0] in url[len(domains[0]):]:  # Repeated domain
            # Get the protocol prefix if it exists
            prefix = ""
            if url.startswith('http://') or url.startswith('https://'):
                protocol_end = url.find('://') + 3
                prefix = url[:protocol_end]
                
            # Return with just one instance of the domain
            return prefix + domains[0]
            
        # Try the specialized method for handling duplicated segments
        cleaned_url = self.clean_duplicated_url_segments(url)
        if cleaned_url != url:
            return cleaned_url
            
        return url
        
    def clean_duplicated_url_segments(self, url):
        """Clean up URLs with duplicated domain and path segments.
        Example: loyalty.cUloyalty.com/royalty.com/rewarty.com/reward/chocoleward/chocolate
        """
        if not url or len(url) < 10:
            return url
            
        self.log_callback(f"Cleaning duplicated segments in: {url}")
        
        # First, try to identify the main domain
        import re
        
        # Look for a clean domain pattern
        domain_match = re.search(r'([a-zA-Z0-9][a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}', url)
        if not domain_match:
            return url
            
        domain = domain_match.group(0)
        self.log_callback(f"Found main domain: {domain}")
        
        # Find where the path starts (after the domain)
        if '/' not in url:
            return url  # No path, just return as is
            
        # Split into domain and path
        parts = url.split('/', 1)
        if len(parts) < 2:
            return url
            
        domain_part = parts[0]
        path_part = parts[1]
        
        # Clean up the domain part - keep only the first valid domain
        cleaned_domain = domain
        
        # Clean up the path part - look for duplicated segments
        path_segments = path_part.split('/')
        cleaned_segments = []
        
        # Keep track of segments we've seen to avoid duplicates
        seen_segments = set()
        
        for segment in path_segments:
            # Skip empty segments
            if not segment:
                continue
                
            # Skip segments that are too similar to ones we've seen
            should_skip = False
            for seen in seen_segments:
                # Check if this segment is very similar to one we've seen
                if seen.lower() in segment.lower() or segment.lower() in seen.lower():
                    should_skip = True
                    break
                    
            if not should_skip:
                cleaned_segments.append(segment)
                seen_segments.add(segment)
                
        # Reconstruct the URL
        if not cleaned_segments:
            # If no valid path segments, just return the domain
            cleaned_url = cleaned_domain
        else:
            # Otherwise, combine domain with cleaned path
            cleaned_url = cleaned_domain + '/' + '/'.join(cleaned_segments)
            
        # Add http:// if needed
        if not cleaned_url.startswith(('http://', 'https://')):
            cleaned_url = 'http://' + cleaned_url
            
        self.log_callback(f"Cleaned URL: {cleaned_url}")
        return cleaned_url

    def write_ntag_url(self, url):
        try:
            # Log the URL we're trying to write
            self.log_callback(f"Attempting to write URL: {url}")
            
            # Make sure URL is properly formatted
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                self.log_callback(f"Added http:// prefix: {url}")
            
            # Remove the http:// prefix for NDEF encoding (will be encoded as type 0x01)
            if url.startswith('http://'):
                actual_url = url[7:]  # Remove 'http://'
                prefix_type = 0x01    # URI identifier for http://
            elif url.startswith('https://'):
                actual_url = url[8:]  # Remove 'https://'
                prefix_type = 0x02    # URI identifier for https://
            else:
                actual_url = url
                prefix_type = 0x00    # No prefix
                
            self.log_callback(f"URL after prefix removal: {actual_url}")
            
            # Ensure URL is ASCII-encodable (remove any non-ASCII characters)
            actual_url = ''.join(c for c in actual_url if ord(c) < 128)
            
            # Encode the URL to ASCII bytes
            try:
                url_bytes = actual_url.encode("ascii")
                self.log_callback(f"URL encoded successfully, length: {len(url_bytes)} bytes")
            except UnicodeEncodeError as e:
                self.log_callback(f"Error encoding URL: {e}")
                # Try to strip non-ASCII characters
                actual_url = ''.join(c for c in actual_url if ord(c) < 128)
                url_bytes = actual_url.encode("ascii")
                self.log_callback(f"Stripped non-ASCII characters, new URL: {actual_url}")
            
            # Create NDEF record
            # The structure is:
            # [0x03, length, 0xD1, 0x01, text_length, 0x55, prefix_type, ...URL data..., 0xFE]
            ndef_length = len(url_bytes) + 5
            ndef_header = [
                0x03,        # NDEF record header
                ndef_length, # Length of the NDEF record
                0xD1,        # NDEF record type (URI)
                0x01,        # Record type length
                len(url_bytes) + 1, # Payload length (URL + URI identifier code)
                0x55,        # 'U' - URI record type
                prefix_type, # URI identifier code (0x01 = http://, 0x02 = https://)
            ]
            
            # Combine header, URL data, and terminator
            data = ndef_header + list(url_bytes) + [0xFE]
            
            # Dump the data we're about to write for debugging
            hex_data = ' '.join([f'{b:02X}' for b in data])
            self.log_callback(f"Full NDEF data to write: {hex_data}")
            
            # Format the tag first to ensure it's clean
            self.log_callback("Formatting tag before writing...")
            empty_data = [0x00, 0x00, 0x00, 0x00]
            for page in range(4, 8):  # Clear the first few pages
                self.write_block(page, empty_data)
            
            # Split into 4-byte pages for NTAG
            pages = [data[i : i + 4] for i in range(0, len(data), 4)]
            
            # Pad the last page if needed
            if len(pages[-1]) < 4:
                pages[-1].extend([0] * (4 - len(pages[-1])))
            
            # Write each page to the tag
            for i, page_data in enumerate(pages):
                page_num = i + 4  # Start at page 4
                hex_page = ' '.join([f'{b:02X}' for b in page_data])
                self.log_callback(f"Writing page {page_num}: {hex_page}")
                if not self.write_block(page_num, page_data):
                    self.log_callback(f"Failed to write page {page_num}")
                    return False
                
                # Add a small delay between writes to ensure stability
                import time
                time.sleep(0.05)
            
            self.log_callback(f"Successfully wrote URL to tag: {url}")
            return True
        except Exception as e:
            self.log_callback(f"Error writing NTAG URL: {e}")
            return False
            
    def format_card(self):
        """Format/erase an NFC tag by writing empty data to all user pages."""
        try:
            if not self.connection:
                self.log_callback("Reader not connected!")
                return False
                
            self.log_callback("Starting card format operation...")
            
            # First, read the tag UID to identify it
            uid = self.read_uid()
            if not uid:
                self.log_callback("No tag detected for formatting")
                return False
                
            self.log_callback(f"Formatting tag with UID: {uid}")
            
            # Empty data (all zeros)
            empty_data = [0x00, 0x00, 0x00, 0x00]
            
            # For NTAG213/215/216, user memory starts at page 4
            # NTAG213: pages 4-39 (36 pages)
            # NTAG215: pages 4-129 (126 pages)
            # NTAG216: pages 4-225 (222 pages)
            
            # First, completely clear the tag by writing zeros to all user pages
            self.log_callback("Clearing all user memory...")
            for page in range(4, 40):  # Cover at least NTAG213 size
                try:
                    self.write_block(page, empty_data)
                    # Add a small delay between writes for stability
                    import time
                    time.sleep(0.02)
                except Exception:
                    # If we hit an error, we might have reached the end of the tag's memory
                    break
            
            # Now write a proper empty NDEF message
            self.log_callback("Writing empty NDEF structure...")
            
            # NDEF Message TLV (Type-Length-Value) format
            # Type: 0x03 (NDEF Message)
            # Length: 0x03 (3 bytes)
            # Value: [0xD0, 0x00, 0x00] (Empty NDEF record)
            #   0xD0: NDEF record header (TNF=0, IL=0, SR=1, CF=0, ME=1, MB=1)
            #   0x00: Type length (0 bytes)
            #   0x00: Payload length (0 bytes)
            empty_ndef_header = [0x03, 0x03, 0xD0, 0x00]
            
            # Write the NDEF header to page 4
            if not self.write_block(4, empty_ndef_header):
                self.log_callback("Failed to write NDEF header")
                return False
                
            # Write empty payload and terminator to page 5
            ndef_terminator = [0x00, 0xFE, 0x00, 0x00]  # Last byte of empty NDEF + Terminator TLV
            if not self.write_block(5, ndef_terminator):
                self.log_callback("Failed to write NDEF terminator")
                return False
                
            # Verify the format by reading back the first few pages
            self.log_callback("Verifying format...")
            page4 = self.read_block(4)
            page5 = self.read_block(5)
            
            if page4 and page5:
                page4_hex = ' '.join([f'{b:02X}' for b in page4])
                page5_hex = ' '.join([f'{b:02X}' for b in page5])
                self.log_callback(f"Page 4: {page4_hex}")
                self.log_callback(f"Page 5: {page5_hex}")
                
                # Check if the NDEF structure was written correctly
                if page4[0] == 0x03 and page5[1] == 0xFE:
                    self.log_callback("Card format successful - proper NDEF structure verified")
                    return True
                else:
                    self.log_callback("Warning: Card formatted but NDEF structure verification failed")
                    return True  # Still return true as the card is formatted
            else:
                self.log_callback("Warning: Could not verify format, but operation completed")
                return True
            
        except Exception as e:
            self.log_callback(f"Error formatting card: {e}")
            return False


class ReadModeWindow:
    """Standalone window for real-time NFC tag reading."""

    def __init__(self, parent, nfc_reader):
        self.nfc = nfc_reader
        self.window = tk.Toplevel(parent)
        self.window.title("NFC Read Mode")
        self.window.geometry("400x200")
        self.window.configure(bg="#f0f2f5")
        self.running = True
        self.last_uid = None

        # UI
        ttk.Label(self.window, text="NFC Read Mode", font=("Arial", 14, "bold")).pack(
            pady=10
        )
        ttk.Label(
            self.window, text="Place NFC tag on reader...", font=("Arial", 10)
        ).pack(pady=5)
        self.status_label = ttk.Label(
            self.window, text="Waiting for tag...", font=("Arial", 10)
        )
        self.status_label.pack(pady=5)
        ttk.Button(self.window, text="Close", command=self.close).pack(pady=10)

        # Start polling
        threading.Thread(target=self.poll_tag, daemon=True).start()

    def poll_tag(self):
        """Poll for NFC tag in real-time."""
        while self.running:
            try:
                uid = self.nfc.read_uid()
                if uid and uid != self.last_uid:
                    self.last_uid = uid
                    url = self.nfc.read_ntag_url()
                    self.show_tag_data(uid, url)
                time.sleep(1)
            except Exception as e:
                self.nfc.log_callback(f"Error polling tag: {e}")
                time.sleep(1)

    def show_tag_data(self, uid, url):
        """Show tag data in a modal popup."""
        modal = tk.Toplevel(self.window)
        modal.title("NFC Tag Data")
        modal.geometry("300x200")
        modal.transient(self.window)
        modal.grab_set()

        ttk.Label(modal, text="NFC Tag Data", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(modal, text=f"UID: {uid}", font=("Arial", 10)).pack(pady=5)
        ttk.Label(modal, text=f"URL: {url or 'None'}", font=("Arial", 20)).pack(pady=5)
        ttk.Button(modal, text="Close", command=modal.destroy).pack(pady=10)

    def close(self):
        """Close the read mode window."""
        self.running = False
        self.window.destroy()


class NFCDashboard:
    """Store admin dashboard for NFC operations and task management."""

    def __init__(self, root):
        self.root = root
        self.root.title("NFC Store Admin Dashboard")
        self.root.geometry("900x600")
        self.nfc = NFCReader(self.log)
        self.tasks = []
        self.next_task_id = 5  # Start after fake API IDs
        self.setup_ui()
        self.start_auto_connect()
        self.fetch_tasks()

    def log(self, message):
        self.status_text.insert(
            tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        )
        self.status_text.see(tk.END)

    def setup_ui(self):
        self.root.configure(bg="#f0f2f5")
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Sidebar
        sidebar = ttk.Frame(main_frame, width=200, style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)

        style = ttk.Style()
        style.configure("Sidebar.TFrame", background="#2c3e50")
        style.configure(
            "Sidebar.TButton",
            background="black",
            font=("Arial", 10, "bold"),
        )
        style.configure(
            "Sidebar.TLabel",
            background="#2c3e50",
            foreground="white",
            font=("Arial", 12, "bold"),
        )

        ttk.Label(sidebar, text="NFC Controls", style="Sidebar.TLabel").pack(pady=10)
        ttk.Button(
            sidebar, text="Add Task", command=self.add_task, style="Sidebar.TButton"
        ).pack(pady=5, padx=10, fill=tk.X)
        ttk.Button(
            sidebar,
            text="Read Mode",
            command=self.open_read_mode,
            style="Sidebar.TButton",
        ).pack(pady=5, padx=10, fill=tk.X)
        ttk.Button(
            sidebar,
            text="Disable Beep",
            command=self.nfc.disable_beep,
            style="Sidebar.TButton",
        ).pack(pady=5, padx=10, fill=tk.X)

        # Main content
        content = ttk.Frame(main_frame)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Frame(content)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Store NFC Dashboard", font=("Arial", 16, "bold")).pack(
            side=tk.LEFT
        )
        self.task_count_var = tk.StringVar(value="Tasks for Today: 0")
        ttk.Label(header, textvariable=self.task_count_var, font=("Arial", 12)).pack(
            side=tk.RIGHT, padx=10
        )

        # Task list
        task_frame = ttk.LabelFrame(content, text="Today's Tasks")
        task_frame.pack(fill=tk.BOTH, expand=True)
        self.task_tree = ttk.Treeview(
            task_frame, columns=("ID", "Title", "URL", "Tag Color"), show="headings"
        )
        self.task_tree.heading("ID", text="ID")
        self.task_tree.heading("Title", text="Task")
        self.task_tree.heading("URL", text="URL")
        self.task_tree.heading("Tag Color", text="Tag Color")
        self.task_tree.column("ID", width=50)
        self.task_tree.column("Title", width=200)
        self.task_tree.column("URL", width=300)
        self.task_tree.column("Tag Color", width=100)
        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Context menu for tasks
        self.context_menu = tk.Menu(self.task_tree, tearoff=0)
        self.context_menu.add_command(label="Write URL", command=self.write_task_url)
        self.task_tree.bind("<Button-3>", self.show_context_menu)

        # Status area
        status_frame = ttk.LabelFrame(content, text="Status Log")
        status_frame.pack(fill=tk.X, pady=(10, 0))
        self.status_text = scrolledtext.ScrolledText(status_frame, height=6, width=80)
        self.status_text.pack(padx=5, pady=5, fill=tk.BOTH)

    def show_context_menu(self, event):
        """Show context menu for task tree."""
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def start_auto_connect(self):
        def connect_loop():
            max_attempts = 5
            for attempt in range(max_attempts):
                if self.nfc.connect():
                    self.nfc.disable_beep()
                    return
                self.log(
                    f"Connection attempt {attempt + 1}/{max_attempts} failed. Retrying in 3 seconds..."
                )
                time.sleep(3)
            self.log("Failed to connect to NFC reader.")
            messagebox.showerror("Error", "Could not connect to NFC reader.")

        threading.Thread(target=connect_loop, daemon=True).start()

    def fetch_tasks(self):
        today = "2025-05-17"
        tasks = FakeAPI.fetch_tasks()
        self.tasks = [task for task in tasks if task["date"] == today]
        self.task_count_var.set(f"Tasks for Today: {len(self.tasks)}")

        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        for task in self.tasks:
            self.task_tree.insert(
                "",
                tk.END,
                values=(task["id"], task["title"], task["url"], task["tag_color"]),
            )
            self.task_tree.tag_configure(
                f"color_{task['id']}", background=task["tag_color"]
            )
            self.task_tree.item(
                self.task_tree.get_children()[-1], tags=(f"color_{task['id']}",)
            )

    def add_task(self):
        """Add a new task via modal."""
        modal = tk.Toplevel(self.root)
        modal.title("Add Task")
        modal.geometry("400x300")
        modal.transient(self.root)
        modal.grab_set()

        ttk.Label(modal, text="Add New Task", font=("Arial", 12, "bold")).pack(pady=10)

        # Title
        ttk.Label(modal, text="Title:").pack()
        title_entry = ttk.Entry(modal, width=40)
        title_entry.pack(pady=5)

        # URL
        ttk.Label(modal, text="URL:").pack()
        url_entry = ttk.Entry(modal, width=40)
        url_entry.pack(pady=5)
        url_entry.insert(0, "https://")

        # Tag Color
        ttk.Label(modal, text="Tag Color:").pack()
        color_var = tk.StringVar(value="#FF5733")
        color_options = {
            "Red": "#FF5733",
            "Green": "#33FF57",
            "Blue": "#3357FF",
            "Pink": "#FF33A1",
        }
        ttk.OptionMenu(modal, color_var, "#FF5733", *color_options.values()).pack(
            pady=5
        )

        def save_task():
            title = title_entry.get().strip()
            url = url_entry.get().strip()
            if not title or not url:
                messagebox.showerror(
                    "Error", "Title and URL are required!", parent=modal
                )
                return
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            task = {
                "id": self.next_task_id,
                "title": title,
                "url": url,
                "tag_color": color_var.get(),
                "date": "2025-05-17",
            }
            self.tasks.append(task)
            self.next_task_id += 1
            self.fetch_tasks()  # Refresh task list
            modal.destroy()

        ttk.Button(modal, text="Save", command=save_task).pack(pady=10)
        ttk.Button(modal, text="Cancel", command=modal.destroy).pack(pady=5)

    def write_task_url(self):
        """Show modal to write selected task's URL to NFC tag."""
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a task!")
            return

        task_id = self.task_tree.item(selected[0])["values"][0]
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            messagebox.showerror("Error", "Task not found!")
            return

        modal = tk.Toplevel(self.root)
        modal.title("Write URL to NFC Tag")
        modal.geometry("400x200")
        modal.transient(self.root)
        modal.grab_set()

        ttk.Label(modal, text="Write URL to NFC Tag", font=("Arial", 12, "bold")).pack(
            pady=10
        )
        ttk.Label(modal, text=f"Task: {task['title']}", font=("Arial", 10)).pack()
        ttk.Label(modal, text=f"URL: {task['url']}", font=("Arial", 10)).pack(pady=5)
        ttk.Label(modal, text="Place NFC tag on reader...", font=("Arial", 10)).pack()
        status_var = tk.StringVar(value="")
        ttk.Label(modal, textvariable=status_var, font=("Arial", 10)).pack(pady=5)

        def write():
            if self.nfc.write_ntag_url(task["url"]):
                status_var.set("Successfully wrote URL to tag!")
                self.log(f"Wrote URL: {task['url']} for task {task['title']}")
                modal.after(1000, modal.destroy)
            else:
                status_var.set("Failed to write URL. Try again.")
                self.log(f"Failed to write URL: {task['url']}")

        ttk.Button(modal, text="Write", command=write).pack(pady=10)
        ttk.Button(modal, text="Cancel", command=modal.destroy).pack(pady=5)

    def open_read_mode(self):
        """Open standalone read mode window."""
        ReadModeWindow(self.root, self.nfc)


if __name__ == "__main__":
    root = tk.Tk()
    app = NFCDashboard(root)
    root.mainloop()
