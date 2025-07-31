# =================================================================================
# Smart Advisor: Learning Path Recommendation App
#
# To run this application, you need to install the following libraries:
# pip install PyQt6 requests beautifulsoup4 together markdown Pygments
# =================================================================================

import sys
import os
import json
import csv
import re
import time
from datetime import datetime
import requests
import markdown
import together
from together import Together
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox, QFileDialog, QMenuBar,
                             QProgressBar)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QAction

# --- Constants and Configuration ---

# API Key for the LLM service.
# IMPORTANT: This key is hardcoded as requested by the user.
API_KEY = "acaf876f035ff654d7994a13412ff847e0185166b2ed942e1b902bf437dfb1fe"

# The system prompt that defines the AI's role and rules.
SYSTEM_PROMPT = """
تو یک مشاور آموزشی و شغلی متخصص در حوزه هوش مصنوعی هستی. وظیفه تو این است که بر اساس لیستی از دوره‌های آموزشی که در اختیار داری، یک مسیر یادگیری شخصی‌سازی شده برای کاربر طراحی کنی.

**تو به لیستی از دوره‌ها و محتوای آن‌ها دسترسی داری. هرگز این لیست یا محتوای خام آن را به کاربر نشان نده.**

**قوانین بسیار مهم مکالمه و خروجی تو:**
*   **خروجی مطلقاً فقط مکالمه:** پاسخ‌های تو باید **فقط و فقط** شامل گفتگوی مستقیم با کاربر باشد. هیچ‌گونه فکر داخلی، تحلیل‌های شخصی از ورودی، جزئیات پردازش (مثل "لیست دوره‌ها دریافت شد")، یا داده‌های خامی مثل URL یا محتوای استخراج شده از دوره‌ها را در پاسخ‌هایت قرار نده.
*   **همیشه به زبان فارسی روان، حرفه‌ای و بدون اشتباه صحبت کن.**
*   **از مارک‌داون (مانند **bold** یا *italics* یا لیست‌های شماره‌گذاری شده) برای خوانایی بیشتر پاسخ‌هایت استفاده کن.**
*   **مکالمه عمیق و گام به گام برای شناخت کاربر:**
    *   **شروع مکالمه:** گفتگو را با پرسیدن **تنها یک سوال کلیدی و عمیق** برای درک هدف اصلی کاربر از یادگیری شروع کن. از کلیشه‌ها پرهیز کن.
    *   **ادامه مکالمه:**
        *   هدف تو این است که با پرسیدن **حداقل ۲ تا ۴ سوال هوشمندانه و مرتبط**، به درک کاملی از موارد زیر برسی:
            1.  **سطح دانش فعلی کاربر** (مبتدی، متوسط، پیشرفته).
            2.  **اهداف شغلی یا شخصی** (مثلاً تغییر شغل، ارتقای مهارت، انجام یک پروژه خاص).
            3.  **میزان زمان آزاد** و تعهدی که کاربر می‌تواند برای یادگیری بگذارد.
        *   هر بار فقط یک سوال بپرس. **عجله نکن!** تا زمانی که تصویر کاملی از نیازهای کاربر به دست نیاورده‌ای، توصیه نهایی را ارائه نده.
*   **توصیه نهایی (مسیر یادگیری):**
    *   توصیه نهایی تو باید یک **مسیر یادگیری مشخص و اولویت‌بندی شده** باشد.
    *   برای هر دوره پیشنهادی، به وضوح **دلیل انتخابت** را توضیح بده و آن را به پاسخ‌هایی که کاربر در طول مکالمه داده است، مرتبط کن. (مثلاً: "چون گفتی به مباحث عملی علاقه داری، این دوره که پروژه محور است برایت عالی است.")
    *   برای هر دوره، یک **تخمین زمانی واقع‌بینانه** برای به اتمام رساندن آن ارائه بده. (مثلاً: "حدود ۴ تا ۶ هفته، با مطالعه روزی ۲ ساعت").
    *   پیشنهاداتت را به صورت یک مسیر منطقی ارائه بده. (مثلاً: "بهتر است با دوره X برای مبانی شروع کنی، سپس به سراغ دوره Y برای یادگیری عمیق‌تر بروی.")

*   **مثال سوال خوب:** "خیلی هم عالی! برای اینکه بتونم دقیق‌ترین مسیر رو برات طراحی کنم، بهم بگو در حال حاضر با کدام یک از مفاهیم هوش مصنوعی (مثلاً یادگیری ماشین، شبکه‌های عصبی) آشنایی داری و در چه سطحی؟"
*   **مثال خروجی ممنوع:** "Okay, I have the course list. Now I will ask the user about their goals. My first question is: What do you want to learn?"
"""

# --- Worker for Threading ---

class Worker(QObject):
    """
    A generic worker that runs a function in a separate thread to prevent the GUI from freezing.
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    # Signal now emits percentage (int) and a status message (str)
    status_update = pyqtSignal(int, str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Pass the worker instance itself as the first argument to the function
            # so that the function can emit signals from the worker.
            result = self.fn(self, *self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"خطایی رخ داد: {e}")

# --- Main Application Window ---

class SmartTeacherApp(QWidget):
    """
    The main application window containing the GUI and the core logic.
    """
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.chat_history = []
        self.course_file_path = "" # To store the path of the selected file
        self._init_ui()
        self._init_menu() # Initialize the menu bar
        self._connect_signals()
        self.reset_chat()

    def _init_ui(self):
        """Initializes the user interface."""
        self.setWindowTitle("مشاور هوشمند: پیشنهاد مسیر یادگیری")
        self.setGeometry(100, 100, 700, 800)

        # Layouts
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        file_layout = QHBoxLayout()
        user_input_layout = QHBoxLayout()

        # --- File Input Section ---
        self.file_path_display = QLineEdit()
        self.file_path_display.setPlaceholderText("فایل متنی حاوی لینک دوره‌ها را انتخاب کنید...")
        self.file_path_display.setReadOnly(True)
        self.select_file_button = QPushButton("انتخاب فایل")
        self.start_button = QPushButton("شروع تحلیل")
        self.select_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)

        file_layout.addWidget(self.file_path_display)
        file_layout.addWidget(self.select_file_button)
        file_layout.addWidget(self.start_button)

        # --- Conversation Display ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # self.chat_display.setFont(QFont("Arial", 14)) # Font is now set in stylesheet

        # --- Status Label ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.hide()

        # --- User Input Section ---
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("پاسخ خود را اینجا تایپ کنید...")
        self.send_button = QPushButton("ارسال پاسخ")
        self.export_button = QPushButton("ذخیره گفتگو")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.hide() # Hidden by default

        user_input_layout.addWidget(self.user_input)
        user_input_layout.addWidget(self.send_button)
        user_input_layout.addWidget(self.export_button)

        # Add widgets to main layout
        self.menu_bar = QMenuBar(self)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(file_layout)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(user_input_layout)

        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """Applies the dark theme stylesheet, including syntax highlighting styles."""
        # CSS for 'monokai' theme from Pygments for code highlighting
        pygments_css = """
        .codehilite .hll { background-color: #49483e }
        .codehilite .c { color: #75715e } /* Comment */
        .codehilite .err { color: #960050; background-color: #1e0010 } /* Error */
        .codehilite .k { color: #66d9ef } /* Keyword */
        .codehilite .l { color: #ae81ff } /* Literal */
        .codehilite .n { color: #f8f8f2 } /* Name */
        .codehilite .o { color: #f92672 } /* Operator */
        .codehilite .p { color: #f8f8f2 } /* Punctuation */
        .codehilite .ch { color: #75715e } /* Comment.Hashbang */
        .codehilite .cm { color: #75715e } /* Comment.Multiline */
        .codehilite .cp { color: #75715e } /* Comment.Preproc */
        .codehilite .cpf { color: #75715e } /* Comment.PreprocFile */
        .codehilite .c1 { color: #75715e } /* Comment.Single */
        .codehilite .cs { color: #75715e } /* Comment.Special */
        .codehilite .gd { color: #f92672 } /* Generic.Deleted */
        .codehilite .ge { font-style: italic } /* Generic.Emph */
        .codehilite .gi { color: #a6e22e } /* Generic.Inserted */
        .codehilite .gs { font-weight: bold } /* Generic.Strong */
        .codehilite .gu { color: #75715e } /* Generic.Subheading */
        .codehilite .kc { color: #66d9ef } /* Keyword.Constant */
        .codehilite .kd { color: #66d9ef } /* Keyword.Declaration */
        .codehilite .kn { color: #f92672 } /* Keyword.Namespace */
        .codehilite .kp { color: #66d9ef } /* Keyword.Pseudo */
        .codehilite .kr { color: #66d9ef } /* Keyword.Reserved */
        .codehilite .kt { color: #66d9ef } /* Keyword.Type */
        .codehilite .ld { color: #e6db74 } /* Literal.Date */
        .codehilite .m { color: #ae81ff } /* Literal.Number */
        .codehilite .s { color: #e6db74 } /* Literal.String */
        .codehilite .na { color: #a6e22e } /* Name.Attribute */
        .codehilite .nb { color: #f8f8f2 } /* Name.Builtin */
        .codehilite .nc { color: #a6e22e } /* Name.Class */
        .codehilite .no { color: #66d9ef } /* Name.Constant */
        .codehilite .nd { color: #a6e22e } /* Name.Decorator */
        .codehilite .ni { color: #f8f8f2 } /* Name.Entity */
        .codehilite .ne { color: #a6e22e } /* Name.Exception */
        .codehilite .nf { color: #a6e22e } /* Name.Function */
        .codehilite .nl { color: #f8f8f2 } /* Name.Label */
        .codehilite .nn { color: #f8f8f2 } /* Name.Namespace */
        .codehilite .nx { color: #a6e22e } /* Name.Other */
        .codehilite .py { color: #f8f8f2 } /* Name.Property */
        .codehilite .nt { color: #f92672 } /* Name.Tag */
        .codehilite .nv { color: #f8f8f2 } /* Name.Variable */
        .codehilite .ow { color: #f92672 } /* Operator.Word */
        .codehilite .w { color: #f8f8f2 } /* Text.Whitespace */
        .codehilite .mb { color: #ae81ff } /* Literal.Number.Bin */
        .codehilite .mf { color: #ae81ff } /* Literal.Number.Float */
        .codehilite .mh { color: #ae81ff } /* Literal.Number.Hex */
        .codehilite .mi { color: #ae81ff } /* Literal.Number.Integer */
        .codehilite .mo { color: #ae81ff } /* Literal.Number.Oct */
        .codehilite .sa { color: #e6db74 } /* Literal.String.Affix */
        .codehilite .sb { color: #e6db74 } /* Literal.String.Backtick */
        .codehilite .sc { color: #e6db74 } /* Literal.String.Char */
        .codehilite .dl { color: #e6db74 } /* Literal.String.Delimiter */
        .codehilite .sd { color: #e6db74 } /* Literal.String.Doc */
        .codehilite .s2 { color: #e6db74 } /* Literal.String.Double */
        .codehilite .se { color: #ae81ff } /* Literal.String.Escape */
        .codehilite .sh { color: #e6db74 } /* Literal.String.Heredoc */
        .codehilite .si { color: #e6db74 } /* Literal.String.Interpol */
        .codehilite .sx { color: #e6db74 } /* Literal.String.Other */
        .codehilite .sr { color: #e6db74 } /* Literal.String.Regex */
        .codehilite .s1 { color: #e6db74 } /* Literal.String.Single */
        .codehilite .ss { color: #e6db74 } /* Literal.String.Symbol */
        .codehilite .bp { color: #f8f8f2 } /* Name.Builtin.Pseudo */
        .codehilite .fm { color: #a6e22e } /* Name.Function.Magic */
        .codehilite .vc { color: #f8f8f2 } /* Name.Variable.Class */
        .codehilite .vg { color: #f8f8f2 } /* Name.Variable.Global */
        .codehilite .vi { color: #f8f8f2 } /* Name.Variable.Instance */
        .codehilite .vm { color: #f8f8f2 } /* Name.Variable.Magic */
        .codehilite .il { color: #ae81ff } /* Literal.Number.Integer.Long */
        .codehilite { background: #272822 !important; color: #f8f8f2 !important; padding: 10px; border-radius: 5px; }
        div.codehilite { margin: 10px 0; }
        """

        self.setStyleSheet(f"""
            QWidget {{
                background-color: #1A1A1A;
                color: #F0F0F0;
                font-family: Arial;
            }}
            {pygments_css}
            QLineEdit {
                background-color: #101010;
                border: 1px solid #444;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QTextEdit {
                background-color: #151515;
                border: 1px solid #444;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #F0F0F0;
                border: 1px solid #555;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                border: 1px solid #666;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QPushButton:disabled {
                background-color: #202020;
                color: #555;
            }
            QLabel {
                font-size: 14px;
            }
        """)
        self.status_label.setStyleSheet("color: #AAA;")

    def _connect_signals(self):
        """Connects widget signals to appropriate slots."""
        self.select_file_button.clicked.connect(self._select_course_file)
        self.start_button.clicked.connect(self._start_evaluation)
        self.send_button.clicked.connect(self._send_user_reply)
        self.export_button.clicked.connect(self._export_chat)
        self.user_input.returnPressed.connect(self._send_user_reply)

    def _set_ui_loading(self, is_loading, message=""):
        """Enables or disables UI elements during long operations."""
        self.select_file_button.setEnabled(not is_loading)
        self.start_button.setEnabled(not is_loading)
        self.user_input.setEnabled(not is_loading)
        self.send_button.setEnabled(not is_loading)
        self.status_label.setText(message)
        QApplication.processEvents() # Force UI update

    def reset_chat(self):
        """Resets the chat history and UI to its initial state."""
        self.chat_history = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        self.chat_display.clear()
        self.user_input.clear()
        self.user_input.setEnabled(False)
        self.send_button.setEnabled(False)

    def _append_message(self, role, text):
        """
        Appends a message to the chat display, styling it as a chat bubble
        and rendering its content from Markdown to HTML.
        """
        # Convert markdown to html, with syntax highlighting
        html_content = markdown.markdown(
            text, extensions=['fenced_code', 'tables', 'codehilite']
        )

        # Determine alignment and bubble color based on role
        if role == 'user':
            # User messages on the right
            align = "right"
            bubble_style = "background-color: #2b5278; color: #f0f0f0; border-top-right-radius: 0;"
            sender_html = "" # No sender name for user
        elif role == 'ai':
            # AI messages on the left
            align = "left"
            bubble_style = "background-color: #363636; color: #f0f0f0; border-top-left-radius: 0;"
            sender_html = "<b style='color:#60A0FF;'>مشاور هوشمند</b><br>"
        else: # System or Error messages
            align = "center"
            bubble_style = "background-color: transparent; color: #999; font-size: 12px;"
            sender_html = ""

        # Create the bubble
        bubble_html = f"""
        <div align='{align}'>
            <div style='display: inline-block; max-width: 80%; text-align: left; padding: 12px; margin-bottom: 8px; border-radius: 15px; {bubble_style}'>
                {sender_html}{html_content}
            </div>
        </div>
        """
        self.chat_display.append(bubble_html)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())


    # --- Core Logic Methods ---

    def _select_course_file(self):
        """Opens a file dialog to select a text file containing course URLs."""
        filters = "Supported Files (*.txt *.csv *.md);;Text Files (*.txt);;CSV Files (*.csv);;Markdown Files (*.md);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل دوره‌ها", "", filters)
        if file_path:
            self.course_file_path = file_path
            self.file_path_display.setText(file_path)

    def _get_cache_path(self, file_path):
        """Generates a corresponding cache file path for a given file path."""
        return f"{file_path}.cache.json"

    def _start_evaluation(self):
        """
        Handles the 'Start Analysis' button click, including checking for a valid cache
        before proceeding with a full analysis.
        """
        if not self.course_file_path:
            QMessageBox.warning(self, "فایل انتخاب نشده", "لطفاً ابتدا یک فایل متنی حاوی لینک‌ها را انتخاب کنید.")
            return

        cache_path = self._get_cache_path(self.course_file_path)

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Validate cache by comparing modification times
                source_file_mod_time = os.path.getmtime(self.course_file_path)
                cached_source_mod_time = cache_data.get("source_mod_time", 0)

                if source_file_mod_time <= cached_source_mod_time:
                    reply = QMessageBox.question(self, "استفاده از کش",
                                                 "یک تحلیل آماده و معتبر برای این فایل پیدا شد. آیا مایل به استفاده از آن هستید؟\n\n"
                                                 "انتخاب 'Yes' از تحلیل ذخیره‌شده استفاده می‌کند. انتخاب 'No' تمام دوره‌ها را مجدداً تحلیل خواهد کرد.",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.Yes)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.reset_chat()
                        self._append_message("system", f"در حال بارگذاری تحلیل از فایل کش: *{cache_path.split('/')[-1]}*")
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(100, lambda: self._on_processing_complete(cache_data["content"]))
                        return
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                print(f"خطا در خواندن یا اعتبارسنجی فایل کش: {e}. کش نادیده گرفته می‌شود.")

        # --- Proceed with full analysis if cache is not used ---
        self.reset_chat()
        self._append_message("user", f"شروع تحلیل دوره‌ها از فایل: *{self.course_file_path.split('/')[-1]}*")
        self.status_label.setText("در حال آماده‌سازی برای تحلیل...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self._set_ui_loading(True)
        self._run_in_thread(self._process_courses_from_file, self.course_file_path, on_finish_slot=self._on_processing_complete)

    def _process_courses_from_file(self, worker, file_path):
        """
        Reads a file with URLs, scrapes each one, and returns the aggregated content.
        This method is designed to be run in a worker thread.
        """
        try:
            urls = []
            if file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip().startswith(('http://', 'https://'))]
            elif file_path.endswith('.csv'):
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        for cell in row:
                            if cell.strip().startswith(('http://', 'https://')):
                                urls.append(cell.strip())
            elif file_path.endswith('.md'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # A simple regex to find URLs in markdown links or plain text
                    urls = re.findall(r'https?://[^\s()<>]+', content)

        except FileNotFoundError:
            raise FileNotFoundError(f"فایل مورد نظر یافت نشد: {file_path}")
        except Exception as e:
            raise IOError(f"خطا در خواندن فایل: {e}")

        if not urls:
            return "" # Return empty if no valid URLs found

        total_urls = len(urls)
        aggregated_results = []
        for i, url in enumerate(urls):
            progress_percent = int(((i + 1) / total_urls) * 100)
            progress_message = f"در حال پردازش دوره {i + 1} از {total_urls}: {url[:70]}..."
            worker.status_update.emit(progress_percent, progress_message)
            try:
                title, content = self._scrape_course_content(url)
                result_block = (
                    f"### Course {i + 1} ###\n"
                    f"**URL:** {url}\n"
                    f"**Title:** {title}\n\n"
                    f"**Content Summary:**\n{content}\n\n"
                    f"----------------------------------------"
                )
                aggregated_results.append(result_block)
            except Exception as e:
                error_message = f"خطا در پردازش لینک {url}: {e}"
                print(error_message) # Log error to console
                # Emit progress but with an error message
                worker.status_update.emit(progress_percent, f"خطا در پردازش دوره {i+1}. از این لینک صرف‌نظر شد.")

        return "\n\n".join(aggregated_results)

    def _on_processing_complete(self, aggregated_content):
        """Callback for when all courses have been scraped and processed."""
        self.progress_bar.hide()
        self.status_label.setText("")

        if not aggregated_content:
            self._on_task_error("هیچ محتوای قابل استفاده‌ای از فایل دوره‌ها استخراج نشد. لطفاً فایل و لینک‌های درون آن را بررسی کنید.")
            return

        # Cache the successful results for future use
        self._cache_results(self.course_file_path, aggregated_content)

        self._append_message("system", "<b>تحلیل تمام دوره‌ها به پایان رسید. گفتگو با مشاور هوشمند آغاز می‌شود...</b>")

        # Prepare the first message for the AI
        initial_user_message = f"محتوای دوره‌های زیر برای تحلیل در اختیار توست:\n\n{aggregated_content}"
        self.chat_history.append({'role': 'user', 'content': initial_user_message})

        self._set_ui_loading(True, "در حال دریافت پاسخ از مشاور هوشمند...")
        self._run_in_thread(self._get_ai_response, self.chat_history, on_finish_slot=self._on_ai_complete)

    def _cache_results(self, original_path, content):
        """Saves the analysis results to a JSON cache file."""
        cache_path = self._get_cache_path(original_path)
        try:
            source_mod_time = os.path.getmtime(original_path)
            cache_data = {
                "content": content,
                "cache_creation_time": datetime.now().isoformat(),
                "source_mod_time": source_mod_time,
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
            print(f"نتایج تحلیل در فایل کش ذخیره شد: {cache_path}")
        except (IOError, FileNotFoundError) as e:
            print(f"خطا در ذخیره فایل کش: {e}")

    def _send_user_reply(self):
        """Handles sending the user's typed reply to the AI."""
        reply = self.user_input.text().strip()
        if not reply:
            return

        self._append_message("user", reply)
        self.user_input.clear()
        self.chat_history.append({'role': 'user', 'content': reply})

        self._set_ui_loading(True, "در حال دریافت پاسخ از استاد هوشمند...")
        self._run_in_thread(self._get_ai_response, self.chat_history, on_finish_slot=self._on_ai_complete)

    def _on_ai_complete(self, ai_response):
        """Callback for when the AI API call is finished."""
        cleaned_response = self._clean_ai_response(ai_response)
        self.chat_history.append({'role': 'assistant', 'content': cleaned_response})
        self._append_message("ai", cleaned_response)
        self._set_ui_loading(False)
        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.user_input.setFocus()

        # Heuristic to detect final recommendation and show the export button
        if "1." in cleaned_response and "2." in cleaned_response or "مسیر یادگیری" in cleaned_response:
            self.export_button.show()

    def _export_chat(self):
        """Saves the current chat content to a text file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گفتگو", "", "Text Files (*.txt);;All Files (*)")

        if file_path:
            try:
                # Use toPlainText() to get the pure text content from the chat display
                chat_content = self.chat_display.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(chat_content)
                QMessageBox.information(self, "موفقیت", f"گفتگو با موفقیت در فایل زیر ذخیره شد:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ذخیره فایل: {e}")

    def _on_task_error(self, error_message):
        """Callback for handling errors from the worker thread."""
        self._append_message("system", f"<b style='color:#FF4040;'>خطا: {error_message}</b>")
        self._set_ui_loading(False)
        self.user_input.setEnabled(False)
        self.send_button.setEnabled(False)

    # --- Helper Functions (executed in worker thread) ---

    def _scrape_course_content(self, url):
        """Fetches and extracts text content from a URL."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            title = soup.title.string.strip() if soup.title else "بدون عنوان"

            # Prioritize semantic tags for content extraction
            content_selectors = ['article', 'main', '.content', '#content', '.post-content']
            content_text = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content_text = element.get_text(separator=' ', strip=True)
                    break

            if not content_text:
                 content_text = soup.body.get_text(separator=' ', strip=True)

            cleaned_text = re.sub(r'\s+', ' ', content_text).strip()
            # Limit content size to avoid excessive API usage
            max_len = 15000
            if len(cleaned_text) > max_len:
                cleaned_text = cleaned_text[:max_len] + "..."

            if not cleaned_text:
                raise ValueError("محتوای متنی قابل استخراجی در صفحه یافت نشد.")

            return title, cleaned_text
        except requests.RequestException as e:
            raise ConnectionError(f"خطا در دسترسی به لینک: {e}")

    def _init_menu(self):
        """Initializes the main menu bar."""
        tools_menu = self.menu_bar.addMenu("ابزارها")

        clear_cache_action = QAction("پاک کردن تمام فایل‌های کش", self)
        clear_cache_action.triggered.connect(self._clear_all_cache)
        tools_menu.addAction(clear_cache_action)

    def _clear_all_cache(self):
        """Finds and deletes all .cache.json files in the current directory."""
        current_dir = os.getcwd()
        cache_files = [f for f in os.listdir(current_dir) if f.endswith(".cache.json")]

        if not cache_files:
            QMessageBox.information(self, "انجام شد", "هیچ فایل کشی برای پاک کردن پیدا نشد.")
            return

        reply = QMessageBox.warning(self, "تاییدیه",
                                      f"شما در حال پاک کردن {len(cache_files)} فایل کش هستید. این کار غیرقابل بازگشت است.\n\nآیا ادامه می‌دهید؟",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            errors = []
            for f in cache_files:
                try:
                    os.remove(os.path.join(current_dir, f))
                    deleted_count += 1
                except OSError as e:
                    errors.append(f)
                    print(f"خطا در پاک کردن فایل {f}: {e}")

            if not errors:
                QMessageBox.information(self, "موفقیت", f"تعداد {deleted_count} فایل کش با موفقیت پاک شد.")
            else:
                QMessageBox.critical(self, "خطا", f"تعداد {deleted_count} فایل پاک شد، اما در پاک کردن فایل‌های زیر خطا رخ داد:\n" + "\n".join(errors))

    def _get_ai_response(self, worker, history):
        """
        Calls the LLM API and returns the response, with an auto-retry mechanism.
        The 'worker' argument is unused but required to match the calling signature from the thread runner.
        """
        retries = 3
        last_exception = None
        for attempt in range(retries):
            try:
                client = Together(api_key=API_KEY)
                response = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-V3",
                    messages=history,
                    max_tokens=1024,
                    temperature=0.7,
                    top_p=0.9,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_exception = e
                # Check for common transient errors, like 503
                if "503" in str(e) or "overloaded" in str(e).lower():
                    print(f"خطای سرویس (تلاش {attempt + 1}/{retries}): {e}. تلاش مجدد در ۳ ثانیه...")
                    time.sleep(3)
                else:
                    # For other errors, don't retry, just raise
                    raise ConnectionError(f"خطا در ارتباط با هوش مصنوعی: {e}")

        # If all retries fail, raise the last captured exception
        raise ConnectionError(f"خطا در ارتباط با هوش مصنوعی پس از {retries} بار تلاش: {last_exception}")

    def _clean_ai_response(self, text):
        """
        Cleans the AI's raw response to remove meta-commentary, thoughts,
        and other non-conversational artifacts.
        """
        # Remove any potential XML-like tags for thinking
        text = re.sub(r'<.*?>', '', text, flags=re.DOTALL)
        # Remove text within brackets or parentheses which often contain metadata
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)

        # Remove common conversational filler and meta-commentary in English/Persian
        starters_to_remove = [
            r'here is my response:', r'here is the question:', r'my question is:',
            r'sure, i can help with that.', r'of course.', r'certainly.',
            r'based on the provided content,', r'after analyzing the text,',
            r'سوال من این است:', r'سوال من:', r'بسیار خب،', r'حتما.', r'البته.',
            r'بر اساس محتوای ارائه شده،', r'پس از تحلیل متن،',
            r'با توجه به اطلاعات دوره،'
        ]
        for starter in starters_to_remove:
            text = re.sub(f'^{starter}', '', text.strip(), flags=re.IGNORECASE | re.UNICODE)

        return text.strip()

    def _run_in_thread(self, fn, *args, on_finish_slot):
        """Utility to create and run a worker thread."""
        self.thread = QThread()
        self.worker = Worker(fn, *args)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(on_finish_slot)
        self.worker.error.connect(self._on_task_error)
        self.worker.status_update.connect(self._update_progress) # Connect status updates

        # Clean up thread and worker after they're done
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _update_progress(self, percent, message):
        """Slot to update the progress bar and status label from the worker thread."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def closeEvent(self, event):
        """Ensure thread is properly terminated on window close."""
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait() # Wait for the thread to finish
        event.accept()

# --- Application Entry Point ---

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SmartTeacherApp()
    window.show()
    sys.exit(app.exec())
