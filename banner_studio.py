#!/usr/bin/env python3
"""
Text User Interface for Banner Printing

A curses-based TUI that runs on Raspberry Pi, allowing users to:
- Select birthdays from birthdays.csv to print
- Create custom banners by typing text
- Preview banners in real-time with scrolling support
- Print selected banners

Layout:
- Left panel: Birthday list + custom text input
- Right panel: Scrollable banner preview
"""

import curses
import csv
import datetime
import os
import time
from typing import List, Tuple, Optional
from banner import banner_lines, send_to_lpr

DEFAULT_CSV = "birthdays.csv"

class BirthdayEntry:
    """Represents a birthday entry from CSV"""
    def __init__(self, first_name: str, alias: str, dob: datetime.date):
        self.first_name = first_name
        self.alias = alias
        self.dob = dob
        self.display_name = alias if alias else first_name
        
    def __str__(self):
        return f"{self.display_name} ({self.dob.strftime('%B %d')})"

def parse_date(date_str: str) -> Optional[datetime.date]:
    """Parse common date formats"""
    date_str = date_str.strip()
    fmts = [
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y",
        "%B %d, %Y", "%b %d, %Y",
        "%m-%d-%Y", "%m-%d-%y",
    ]
    for fmt in fmts:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            pass
    return None

def load_birthdays(csv_file: str = DEFAULT_CSV) -> Tuple[List[BirthdayEntry], Optional[str]]:
    """Load birthdays from CSV file. Returns (birthdays, error_message)"""
    birthdays = []
    
    if not os.path.exists(csv_file):
        return birthdays, f"File not found: {csv_file}"
        
    try:
        with open(csv_file, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            # Check for required columns
            if reader.fieldnames is None:
                return birthdays, f"Empty or invalid CSV file: {csv_file}"
            
            # Create case-insensitive column mapping
            col_map = {col.lower(): col for col in reader.fieldnames}
            
            # Check for required columns (case-insensitive)
            if "first name" not in col_map and "date of birth" not in col_map:
                return birthdays, f"Missing required columns: First Name, Date of Birth"
            elif "first name" not in col_map:
                return birthdays, f"Missing required column: First Name"
            elif "date of birth" not in col_map:
                return birthdays, f"Missing required column: Date of Birth"
            
            # Get actual column names
            first_col = col_map["first name"]
            dob_col = col_map["date of birth"]
            alias_col = col_map.get("alias")
            
            for row in reader:
                first = row.get(first_col, "").strip()
                alias = row.get(alias_col, "").strip() if alias_col else ""
                dob_str = row.get(dob_col, "").strip()
                
                if not dob_str:
                    continue
                    
                dob = parse_date(dob_str)
                if dob and (alias or first):
                    birthdays.append(BirthdayEntry(first, alias, dob))
                    
        # Sort by month, then day
        birthdays.sort(key=lambda b: (b.dob.month, b.dob.day))
    except Exception as e:
        return birthdays, f"Error reading CSV: {str(e)}"
        
    return birthdays, None

class BannerTUI:
    """Main TUI application for banner printing"""
    
    def __init__(self, stdscr, csv_file: str = DEFAULT_CSV):
        self.stdscr = stdscr
        self.csv_file = csv_file
        self.birthdays, load_error = load_birthdays(csv_file)
        if load_error:
            self.show_error_dialog(load_error)
        self.selected_idx = 0
        self.birthday_scroll = 0  # Scroll offset for birthday list
        self.birthday_visible_height = 15  # Will be updated dynamically
        self.custom_text = ""
        self.mode = "birthday"  # "birthday" or "custom"
        self.preview_lines = []
        self.preview_scroll = 0
        self.preview_h_scroll = 0  # Horizontal scroll offset
        self.message = ""
        
        # Initialize curses settings
        curses.curs_set(0)  # Hide cursor
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLUE, -1)  # Highlight - blue on default
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Headers - white on blue
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Messages (default background)
        curses.init_pair(4, curses.COLOR_CYAN, -1)   # Custom text (default background)
        curses.init_pair(5, curses.COLOR_BLUE, -1)  # Preview borders (default background)
        
        self.update_preview()
    
    def reload_csv(self, csv_file: str = None):
        """Reload birthdays from CSV file"""
        if csv_file:
            self.csv_file = csv_file
        self.birthdays, load_error = load_birthdays(self.csv_file)
        self.selected_idx = 0
        self.birthday_scroll = 0
        
        if load_error:
            self.show_error_dialog(load_error)
            self.message = f"Error loading {self.csv_file}"
        elif self.birthdays:
            self.message = f"Loaded {len(self.birthdays)} birthdays from {self.csv_file}"
        else:
            self.message = f"No birthdays found in {self.csv_file}"
        self.update_preview()
    
    def prompt_for_file(self) -> Optional[str]:
        """Prompt user to enter a CSV filename"""
        # Save cursor state
        old_curs = curses.curs_set(1)  # Show cursor
        
        h, w = self.stdscr.getmaxyx()
        # Create a prompt window
        prompt_win = curses.newwin(3, min(60, w - 4), h // 2 - 1, (w - min(60, w - 4)) // 2)
        prompt_win.keypad(True)  # Enable keypad mode for special keys
        prompt_win.box()
        prompt_win.addstr(0, 2, " Open CSV File ", curses.color_pair(2) | curses.A_BOLD)
        prompt_win.addstr(1, 2, "File: ")
        prompt_win.refresh()
        
        # Input field
        input_str = self.csv_file
        cursor_pos = len(input_str)
        
        while True:
            # Display current input
            display_str = input_str if len(input_str) < 50 else "..." + input_str[-47:]
            prompt_win.addstr(1, 8, " " * 50)  # Clear line
            prompt_win.addstr(1, 8, display_str)
            # Position cursor
            display_cursor = min(cursor_pos, 49)
            if len(input_str) >= 50:
                display_cursor = min(cursor_pos - (len(input_str) - 47), 49)
            prompt_win.move(1, 8 + display_cursor)
            prompt_win.refresh()
            
            key = prompt_win.getch()
            
            if key == -1:  # No input
                continue
            elif key == 27:  # ESC - cancel
                curses.curs_set(old_curs)
                return None
            elif key == ord('\n') or key == 10 or key == curses.KEY_ENTER:  # Enter - accept
                curses.curs_set(old_curs)
                return input_str if input_str else None
            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                if cursor_pos > 0:
                    input_str = input_str[:cursor_pos-1] + input_str[cursor_pos:]
                    cursor_pos -= 1
            elif key == curses.KEY_DC or key == 330:  # Delete
                if cursor_pos < len(input_str):
                    input_str = input_str[:cursor_pos] + input_str[cursor_pos+1:]
            elif key == curses.KEY_LEFT or key == 260:
                cursor_pos = max(0, cursor_pos - 1)
            elif key == curses.KEY_RIGHT or key == 261:
                cursor_pos = min(len(input_str), cursor_pos + 1)
            elif key == curses.KEY_HOME or key == 262:
                cursor_pos = 0
            elif key == curses.KEY_END or key == 360:
                cursor_pos = len(input_str)
            elif 32 <= key <= 126:  # Printable characters
                input_str = input_str[:cursor_pos] + chr(key) + input_str[cursor_pos:]
                cursor_pos += 1
    
    def show_error_dialog(self, error_message: str):
        """Show an error dialog with the given message"""
        h, w = self.stdscr.getmaxyx()
        
        # Wrap message to fit in dialog
        max_width = min(60, w - 8)
        lines = []
        words = error_message.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_width - 4:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Create error window
        dialog_height = min(len(lines) + 4, h - 4)
        dialog_width = min(max_width, w - 4)
        dialog_win = curses.newwin(dialog_height, dialog_width, 
                                   (h - dialog_height) // 2, 
                                   (w - dialog_width) // 2)
        dialog_win.box()
        dialog_win.addstr(0, 2, " Error ", curses.color_pair(3) | curses.A_BOLD)
        
        # Display message lines
        for i, line in enumerate(lines[:dialog_height - 4]):
            dialog_win.addstr(i + 2, 2, line)
        
        # Show prompt
        prompt = "Press any key to continue"
        dialog_win.addstr(dialog_height - 2, (dialog_width - len(prompt)) // 2, 
                         prompt, curses.A_DIM)
        dialog_win.refresh()
        
        # Wait for keypress
        dialog_win.getch()
        
    def get_current_text(self) -> str:
        """Get the current text to preview/print"""
        if self.mode == "custom":
            return self.custom_text
        elif self.birthdays and 0 <= self.selected_idx < len(self.birthdays):
            bday = self.birthdays[self.selected_idx]
            return f"Happy Birthday {bday.display_name}!"
        return ""
        
    def update_preview(self):
        """Generate banner preview for current selection"""
        text = self.get_current_text()
        if text:
            self.preview_lines = banner_lines(
                text,
                page_lines=66,
                page_cols=80,
                rotate="cw",
                h_space=1,
                zoom=0
            )
            # Auto-scroll to show the first letter (find first non-space character)
            self.preview_scroll = 0
            self.preview_h_scroll = 0
            
            # Find the first and last lines with actual content (not just border or spaces)
            self.content_start_line = None
            self.content_end_line = None
            
            for i, line in enumerate(self.preview_lines):
                # Skip page borders
                if i % 66 == 0:
                    continue
                # Check if line has any non-space characters in the middle (not just borders)
                content = line.strip('| ')
                if content:
                    if self.content_start_line is None:
                        self.content_start_line = i
                        # Scroll to show it with a bit of context above
                        self.preview_scroll = max(0, i - 5)
                    self.content_end_line = i
        else:
            self.preview_lines = []
            self.preview_scroll = 0
            self.preview_h_scroll = 0
            self.content_start_line = None
            self.content_end_line = None
        
    def draw_left_panel(self, win, h: int, w: int):
        """Draw the left panel with birthday list and custom input"""
        win.erase()
        win.box()
        
        # Header
        title = " Banner Selection "
        win.addstr(0, (w - len(title)) // 2, title, curses.color_pair(2) | curses.A_BOLD)
        
        y = 2
        
        # Mode selector
        bday_marker = "▶" if self.mode == "birthday" else " "
        custom_marker = "▶" if self.mode == "custom" else " "
        
        # Birthday list - only show when in birthday mode
        if self.mode == "birthday":
            win.addstr(y, 2, f"{bday_marker} Birthday Banners", 
                      curses.color_pair(1) | curses.A_BOLD)
            y += 1
        
        if self.mode == "birthday" and self.birthdays:
            list_start_y = y
            # Calculate list height based on whether controls are shown
            controls_height = 9 if h >= 14 else 0
            list_height = h - y - controls_height - 2  # Available space for list
            self.birthday_visible_height = list_height  # Store for scroll calculations
            
            # Show scrollable birthday list
            for i in range(self.birthday_scroll, min(len(self.birthdays), self.birthday_scroll + list_height)):
                if h >= 14 and y >= h - 9:
                    break
                elif h < 14 and y >= h - 2:
                    break
                    
                bday = self.birthdays[i]
                prefix = "  → " if i == self.selected_idx and self.mode == "birthday" else "    "
                text = f"{prefix}{bday}"
                
                if len(text) > w - 3:
                    text = text[:w-6] + "..."
                    
                attr = curses.color_pair(1) if i == self.selected_idx and self.mode == "birthday" else curses.A_NORMAL
                try:
                    win.addstr(y, 2, text, attr)
                except curses.error:
                    pass
                y += 1
                
            # Show scroll indicator if needed
            if len(self.birthdays) > list_height:
                scroll_info = f" [{self.selected_idx + 1}/{len(self.birthdays)}] "
                try:
                    win.addstr(list_start_y - 1, w - len(scroll_info) - 2, scroll_info, curses.A_DIM)
                except curses.error:
                    pass
        elif self.mode == "birthday":
            # Show the actual filename that was attempted (only in birthday mode)
            msg = f"  (No {self.csv_file} found)"
            if len(msg) > w - 4:
                msg = f"  (File not found)"
            win.addstr(y, 2, msg, curses.A_DIM)
            y += 1
            
        if self.mode == "birthday":
            y += 1
        
        # Custom text input - only show when in custom mode
        if self.mode == "custom":
            win.addstr(y, 2, f"{custom_marker} Custom Banner", 
                      curses.color_pair(1) | curses.A_BOLD)
            y += 1
            
            win.addstr(y, 2, "  Text: ", curses.color_pair(4))
            input_text = self.custom_text + "_"
            if len(input_text) > w - 11:
                input_text = "..." + input_text[-(w-14):]
            win.addstr(y, 9, input_text, curses.color_pair(4) | curses.A_BOLD)
            y += 2
        
        # Instructions - only show if there's enough space (at least 14 lines from bottom)
        if h >= 14:
            y = h - 9
            win.addstr(y, 2, "Controls:", curses.color_pair(3) | curses.A_BOLD)
            y += 1
            win.addstr(y, 2, "↑/↓    : Navigate birthdays")
            y += 1
            win.addstr(y, 2, "←/→    : Scroll preview H")
            y += 1
            win.addstr(y, 2, "PgUp/Dn: Scroll preview V")
            y += 1
            win.addstr(y, 2, "TAB    : Birthday/Custom")
            y += 1
            win.addstr(y, 2, "Ctrl+O : Open CSV file")
            y += 1
            win.addstr(y, 2, "Ctrl+P : Print banner")
            y += 1
            win.addstr(y, 2, "ESC    : Quit")
        
        win.refresh()
        
    def draw_right_panel(self, win, h: int, w: int):
        """Draw the right panel with banner preview"""
        win.erase()
        win.box()
        
        # Header with current text
        current_text = self.get_current_text()
        if current_text:
            # Calculate number of pages
            num_pages = (len(self.preview_lines) + 65) // 66 if hasattr(self, 'preview_lines') and self.preview_lines else 0
            if num_pages > 0:
                title = f" {current_text} - {num_pages} page{'s' if num_pages != 1 else ''} "
            else:
                title = f" {current_text} "
            if len(title) > w - 4:
                title = title[:w-7] + "..."
        else:
            title = " Banner Preview "
        win.addstr(0, (w - len(title)) // 2, title, curses.color_pair(2) | curses.A_BOLD)
        
        # Preview area
        preview_h = h - 4
        preview_w = w - 4
        
        # Reserve space for vertical text indicator if we have text
        text_indicator_width = 3 if current_text else 0
        available_preview_w = preview_w - text_indicator_width
        
        if self.preview_lines:
            # Show scrollable preview with page borders
            # Add 1 to max_scroll to allow showing final border
            max_scroll = max(0, len(self.preview_lines) - preview_h + 1)
            self.preview_scroll = min(self.preview_scroll, max_scroll)
            
            # Calculate centering offset for 82-char wide preview (80 chars + 2 borders)
            page_width = 82
            if available_preview_w >= page_width:
                # Center the page in the available space
                left_offset = 2 + (available_preview_w - page_width) // 2
                display_width = page_width
                self.preview_h_scroll = 0  # No horizontal scroll needed
                max_h_scroll = 0
            else:
                # Window is too narrow, allow horizontal scrolling
                left_offset = 2
                display_width = available_preview_w
                max_h_scroll = max(0, page_width - available_preview_w)
                self.preview_h_scroll = min(self.preview_h_scroll, max_h_scroll)
                self.preview_h_scroll = max(0, self.preview_h_scroll)
            
            for i in range(preview_h):
                line_idx = self.preview_scroll + i
                
                # Check if we're at the end and should show the final border
                if line_idx == len(self.preview_lines):
                    # Show final closing border
                    border = "+" + "-" * 80 + "+"
                    border = border[self.preview_h_scroll:self.preview_h_scroll + display_width]
                    try:
                        win.addstr(2 + i, left_offset, border, curses.color_pair(5))
                    except curses.error:
                        pass
                    continue
                
                if line_idx < len(self.preview_lines):
                    # Check if this is a page boundary (every 66 lines)
                    # Show border at start of first page and between pages
                    is_page_break = (line_idx % 66) == 0
                    
                    line = self.preview_lines[line_idx]
                    
                    # Draw page border at breaks
                    if is_page_break:
                        border = "+" + "-" * 80 + "+"
                        # Apply horizontal scroll if needed
                        border = border[self.preview_h_scroll:self.preview_h_scroll + display_width]
                        try:
                            win.addstr(2 + i, left_offset, border, curses.color_pair(5))
                        except curses.error:
                            pass
                        continue
                    
                    # Draw content line with left and right borders
                    content = line[:80] if len(line) >= 80 else (line + " " * (80 - len(line)))
                    display_line = "|" + content + "|"
                    
                    # Apply horizontal scroll if needed
                    display_line = display_line[self.preview_h_scroll:self.preview_h_scroll + display_width]
                    
                    # Draw with color_pair(5) for the borders
                    try:
                        # Draw left border if visible
                        if self.preview_h_scroll == 0:
                            win.addstr(2 + i, left_offset, "|", curses.color_pair(5))
                            win.addstr(2 + i, left_offset + 1, display_line[1:])
                        else:
                            win.addstr(2 + i, left_offset, display_line)
                        
                        # Draw right border if visible
                        if self.preview_h_scroll + display_width >= 82:
                            # Calculate position of the right border
                            right_pos = left_offset + min(display_width - 1, len(display_line) - 1)
                            win.addstr(2 + i, right_pos, "|", curses.color_pair(5))
                    except curses.error:
                        pass
            
            # Draw vertical text indicator on the right
            if current_text and text_indicator_width > 0 and hasattr(self, 'content_start_line') and self.content_start_line is not None:
                # Add visual markers for beginning and end of text
                display_text = "▼" + current_text + "▲"
                
                # Calculate which letters are visible based on scroll position
                # Only count the actual content lines, not the padding
                content_height = self.content_end_line - self.content_start_line + 1 if self.content_end_line else 0
                # Account for the added markers in the calculation
                lines_per_letter = content_height / len(current_text) if len(current_text) > 0 and content_height > 0 else 0
                
                indicator_x = w - text_indicator_width
                
                # Determine visible letter range based on actual content
                first_visible_line = max(self.preview_scroll, self.content_start_line)
                last_visible_line = min(self.preview_scroll + preview_h - 1, self.content_end_line)
                
                # Calculate which letters are visible (in the original text, not including markers)
                if lines_per_letter > 0 and first_visible_line >= self.content_start_line:
                    first_visible_letter = int((first_visible_line - self.content_start_line) / lines_per_letter)
                    last_visible_letter = min(int((last_visible_line - self.content_start_line) / lines_per_letter), len(current_text) - 1)
                    
                    # Check if we're showing padding before content (highlight start marker)
                    if self.preview_scroll < self.content_start_line:
                        # We're in the padding before content, highlight the start marker
                        first_visible_display = 0
                        last_visible_display = 0
                    # Check if we're showing padding after content (highlight end marker)
                    elif self.preview_scroll > self.content_end_line:
                        # We're in the padding after content, highlight the end marker
                        first_visible_display = len(display_text) - 1
                        last_visible_display = len(display_text) - 1
                    else:
                        # Normal content viewing - adjust for the marker at the beginning
                        first_visible_display = first_visible_letter + 1  # +1 for the ▼ marker
                        last_visible_display = last_visible_letter + 1
                else:
                    first_visible_display = -1
                    last_visible_display = -1
                
                # Calculate vertical scroll for the text indicator
                # Make sure the first highlighted character is visible
                available_indicator_height = h - 4  # Space available for letters
                
                if first_visible_display >= 0:
                    # Initialize or maintain text indicator scroll offset
                    if not hasattr(self, 'text_indicator_scroll'):
                        self.text_indicator_scroll = 0
                    
                    # Auto-scroll to keep highlighted letters visible
                    if first_visible_display < self.text_indicator_scroll:
                        # Scroll up to show first highlighted character
                        self.text_indicator_scroll = first_visible_display
                    elif first_visible_display >= self.text_indicator_scroll + available_indicator_height:
                        # Scroll down to show first highlighted character
                        self.text_indicator_scroll = first_visible_display - available_indicator_height + 1
                    
                    # Also check if last highlighted character is visible
                    if last_visible_display >= self.text_indicator_scroll + available_indicator_height:
                        # Scroll to show last highlighted character with some context
                        self.text_indicator_scroll = max(0, last_visible_display - available_indicator_height + 1)
                    
                    # Clamp scroll to valid range
                    max_scroll = max(0, len(display_text) - available_indicator_height)
                    self.text_indicator_scroll = max(0, min(self.text_indicator_scroll, max_scroll))
                else:
                    if not hasattr(self, 'text_indicator_scroll'):
                        self.text_indicator_scroll = 0
                
                # Draw each letter of the display text vertically, one per line
                start_y = 2
                for char_idx, char in enumerate(display_text):
                    # Skip letters that are scrolled out of view
                    display_idx = char_idx - self.text_indicator_scroll
                    if display_idx < 0 or display_idx >= available_indicator_height:
                        continue
                    
                    # Replace spaces with a visible character
                    display_char = "·" if char == " " else char
                    
                    # Determine highlighting
                    is_highlighted = first_visible_display <= char_idx <= last_visible_display
                    is_marker = char_idx == 0 or char_idx == len(display_text) - 1
                    
                    if is_highlighted:
                        attr = curses.color_pair(4) | curses.A_BOLD
                    elif is_marker:
                        # Markers dim when not highlighted
                        attr = curses.color_pair(0) | curses.A_DIM
                    else:
                        attr = curses.A_DIM
                    
                    try:
                        win.addstr(start_y + display_idx, indicator_x, display_char, attr)
                    except curses.error:
                        pass
                        
            # Scroll indicators
            indicators = []
            if len(self.preview_lines) > preview_h:
                # Recalculate max_scroll to ensure it's current (adding 1 for final border)
                current_max_scroll = max(0, len(self.preview_lines) - preview_h + 1)
                # Calculate percentage based on scroll position
                scroll_pct = int((self.preview_scroll / current_max_scroll) * 100) if current_max_scroll > 0 else 100
                indicators.append(f"[{scroll_pct}%] PgUp/PgDn")
            if max_h_scroll > 0:
                indicators.append(f"←/→")
            
            if indicators:
                scroll_info = " " + " ".join(indicators) + " "
                try:
                    win.addstr(h - 2, w - len(scroll_info) - 2, scroll_info, curses.color_pair(3))
                except curses.error:
                    pass
        else:
            msg = "No preview available"
            win.addstr(h // 2, (w - len(msg)) // 2, msg, curses.A_DIM)
            
        win.refresh()
        
    def draw_message(self, win, w: int):
        """Draw status message at bottom"""
        if self.message:
            win.erase()
            msg = f" {self.message} "
            try:
                win.addstr(0, (w - len(msg)) // 2, msg, curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
            win.refresh()
            
    def handle_input(self, key):
        """Handle keyboard input"""
        self.message = ""
        
        if key == 27:  # ESC key
            return False
            
        elif key == ord('\t'):  # TAB
            self.mode = "custom" if self.mode == "birthday" else "birthday"
            self.update_preview()
            
        elif key == curses.KEY_UP:
            if self.mode == "birthday" and self.birthdays:
                self.selected_idx = max(0, self.selected_idx - 1)
                # Adjust scroll to keep selection visible
                if self.selected_idx < self.birthday_scroll:
                    self.birthday_scroll = self.selected_idx
                self.update_preview()
                
        elif key == curses.KEY_DOWN:
            if self.mode == "birthday" and self.birthdays:
                self.selected_idx = min(len(self.birthdays) - 1, self.selected_idx + 1)
                # Adjust scroll to keep selection visible using actual calculated height
                if self.selected_idx >= self.birthday_scroll + self.birthday_visible_height:
                    self.birthday_scroll = self.selected_idx - self.birthday_visible_height + 1
                self.update_preview()
                
        elif key == curses.KEY_LEFT:
            # Scroll preview left
            if self.preview_lines:
                self.preview_h_scroll = max(0, self.preview_h_scroll - 5)
                
        elif key == curses.KEY_RIGHT:
            # Scroll preview right
            if self.preview_lines:
                self.preview_h_scroll += 5
                
        elif key == curses.KEY_PPAGE:  # Page Up - scroll preview in all modes
            if self.preview_lines:
                self.preview_scroll = max(0, self.preview_scroll - 10)
                
        elif key == curses.KEY_NPAGE:  # Page Down - scroll preview in all modes
            if self.preview_lines:
                # Calculate proper max scroll based on current window size
                h, w = self.stdscr.getmaxyx()
                preview_h = h - 1 - 4  # Account for window borders and status
                max_scroll = max(0, len(self.preview_lines) - preview_h + 1)
                self.preview_scroll = min(max_scroll, self.preview_scroll + 10)
                
        elif self.mode == "custom":
            # Handle text input in custom mode FIRST (before print check)
            if key == curses.KEY_BACKSPACE or key == 127:
                if self.custom_text:
                    self.custom_text = self.custom_text[:-1]
                    self.update_preview()
            elif key == curses.KEY_DC:  # Delete key
                self.custom_text = ""
                self.update_preview()
            elif 32 <= key <= 126:  # Printable characters (including p/P)
                if len(self.custom_text) < 50:  # Limit length
                    self.custom_text += chr(key)
                    self.update_preview()
                    
        elif key == 16:  # Ctrl+P (works in both modes)
            text = self.get_current_text()
            if text and self.preview_lines:
                try:
                    send_to_lpr(self.preview_lines)
                    self.message = f"Printing: {text}"
                except Exception as e:
                    self.message = f"Print error: {str(e)}"
            else:
                self.message = "No banner to print"
        
        elif key == 15:  # Ctrl+O - open/reload CSV
            new_file = self.prompt_for_file()
            if new_file:
                self.reload_csv(new_file)
                    
        return True
        
    def run(self):
        """Main TUI loop"""
        # # Set background and clear
        self.stdscr.bkgd(' ', curses.A_NORMAL)
        self.stdscr.clear()
        self.stdscr.refresh()
        
        # Draw the initial display before waiting for any input
        h, w = self.stdscr.getmaxyx()
        left_w = min(40, w // 3)
        right_w = w - left_w - 1
        
        left_win = curses.newwin(h - 1, left_w, 0, 0)
        right_win = curses.newwin(h - 1, right_w, 0, left_w)
        msg_win = curses.newwin(1, w, h - 1, 0)
        
        self.draw_left_panel(left_win, h - 1, left_w)
        self.draw_right_panel(right_win, h - 1, right_w)
        self.draw_message(msg_win, w)
        
        # self.stdscr.nodelay(True)  # Non-blocking mode - keeps display visible
                
        while True:
            # Get input
            key = self.stdscr.getch()
            
            # Small sleep to avoid CPU spinning when no input
            if key == -1:
                time.sleep(0.05)
                continue
            
            if not self.handle_input(key):
                break
            
            # Redraw after handling input
            h, w = self.stdscr.getmaxyx()
            
            # Calculate panel sizes
            left_w = min(40, w // 3)
            right_w = w - left_w - 1
            
            # Create windows
            left_win = curses.newwin(h - 1, left_w, 0, 0)
            right_win = curses.newwin(h - 1, right_w, 0, left_w)
            msg_win = curses.newwin(1, w, h - 1, 0)
            
            # Draw panels
            self.draw_left_panel(left_win, h - 1, left_w)
            self.draw_right_panel(right_win, h - 1, right_w)
            self.draw_message(msg_win, w)

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Interactive banner printing TUI")
    parser.add_argument("csv_file", nargs="?", default=DEFAULT_CSV,
                       help=f"Birthday CSV file (default: {DEFAULT_CSV})")
    args = parser.parse_args()
    
    def run_tui(stdscr):
        tui = BannerTUI(stdscr, csv_file=args.csv_file)
        tui.run()
        
    curses.wrapper(run_tui)

if __name__ == "__main__":
    main()
