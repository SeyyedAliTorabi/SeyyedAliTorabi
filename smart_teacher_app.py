# =================================================================================
# Smart Teacher: Course Evaluation App
#
# To run this application, you need to install the following libraries:
# pip install PyQt6 requests beautifulsoup4 together
# =================================================================================

import sys
import re
import requests
import together
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QTextEdit, QLabel, QMessageBox)
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

# --- Constants and Configuration ---

# API Key for the LLM service.
# IMPORTANT: This key is hardcoded as requested by the user.
API_KEY = "acaf876f035ff654d7994a13412ff847e0185166b2ed942e1b902bf437dfb1fe"

# The system prompt that defines the AI's role and rules.
SYSTEM_PROMPT = """
تو یک معلم باتجربه و دلسوز هستی که در ارزیابی دوره‌های آنلاین تخصص داری. هدف اصلی تو راهنمایی کاربران به سمت بهترین مسیرهای یادگیری از طریق یک مکالمه طبیعی و گام به گام است.

**پاسخ‌های تو باید کاملاً و صرفاً شامل مکالمه با کاربر باشد. هیچ‌گونه اطلاعات اضافی، فکر داخلی، خلاصه‌سازی ورودی، تحلیل‌های خودت از محتوا، جزئیات فرایند پردازش (مثل "محتوا دریافت شد"، "در حال تحلیل هستم")، یا داده‌های خامی را در پاسخ‌هایت به کاربر قرار نده.**

**قوانین بسیار مهم خروجی تو:**
* **خروجی مطلقاً فقط مکالمه:** پاسخ‌های تو باید شامل هیچ‌گونه فکر داخلی، تحلیل‌های خودت از ورودی، جزئیات فرایند پردازش (مثل "محتوا دریافت شد"، "در حال تحلیل هستم")، یا داده‌های خامی مثل URL، محتوای استخراج شده‌ی دوره، یا نقل قول از ورودی خودت نباشد.
* **همیشه به زبان فارسی روان و بدون اشتباه صحبت کن.**
* **پرسش تک به تک:**
    * **اولین پاسخ (پس از دریافت محتوای دوره):** تنها و تنها یک سوال مشخص و عمیق از کاربر بپرس تا اهداف یادگیری، سطح فعلی مهارت‌ها یا دانش قبلی او را بهتر درک کنی. به هیچ وجه چند سوال را همزمان مطرح نکن، توصیه‌ای ارائه نده، یا خلاصه دوره را نگوی.
    * **پاسخ‌های بعدی (پس از پاسخ کاربر):**
        * پاسخ کاربر را تحلیل کن.
        * اگر به اطلاعات بیشتری نیاز داری، **فقط یک سوال پیگیری دیگر** بپرس.
        * اگر اطلاعات کافی را به دست آورده‌ای، **بلافاصله توصیه نهایی خود را ارائه کن.**
* **توصیه نهایی:** توصیه‌ی نهایی تو باید به وضوح بیان کند که آیا دوره برای کاربر **مناسب است یا خیر**. **حتماً دلایل** پشت توصیه‌ی خود را به صورت صریح توضیح بده، و ارزیابی‌ات را به محتوای دوره و نیازها و اهداف اعلام شده توسط کاربر مرتبط کن.
* **مثال (اگر هوش مصنوعی این را بپرسد، این درست است):** "برای اینکه بتوانم بهتر راهنماییتان کنم، لطفاً بگویید هدف اصلی شما از یادگیری این مبحث چیست؟"
* **مثال (اگر هوش مصنوعی این را بپرسد، این اشتباه است - این نوع خروجی کاملاً ممنوع است):** "I see the user provided a course URL... My job is to ask one deep, specific question... Based on the content, what is your prior experience with Python?"
"""

# --- Worker for Threading ---

class Worker(QObject):
    """
    A generic worker that runs a function in a separate thread to prevent the GUI from freezing.
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
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
        self._init_ui()
        self._connect_signals()
        self.reset_chat()

    def _init_ui(self):
        """Initializes the user interface."""
        self.setWindowTitle("استاد هوشمند: ارزیابی دوره آموزشی")
        self.setGeometry(100, 100, 700, 800)

        # Layouts
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        url_layout = QHBoxLayout()
        user_input_layout = QHBoxLayout()

        # --- URL Input Section ---
        url_label = QLabel("لینک دوره:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("لینک دوره آموزشی مورد نظر را اینجا وارد کنید...")
        self.check_button = QPushButton("بررسی دوره")
        self.check_button.setCursor(Qt.CursorShape.PointingHandCursor)

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.check_button)

        # --- Conversation Display ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Arial", 14))

        # --- Status Label ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- User Input Section ---
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("پاسخ خود را اینجا تایپ کنید...")
        self.send_button = QPushButton("ارسال پاسخ")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)

        user_input_layout.addWidget(self.user_input)
        user_input_layout.addWidget(self.send_button)

        # Add widgets to main layout
        main_layout.addLayout(url_layout)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(user_input_layout)

        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """Applies the dark theme stylesheet."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                color: #F0F0F0;
                font-family: Arial;
            }
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
                padding: 15px;
                border-radius: 5px;
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
        self.check_button.clicked.connect(self._start_course_check)
        self.url_input.returnPressed.connect(self._start_course_check)
        self.send_button.clicked.connect(self._send_user_reply)
        self.user_input.returnPressed.connect(self._send_user_reply)

    def _set_ui_loading(self, is_loading, message=""):
        """Enables or disables UI elements during long operations."""
        self.url_input.setEnabled(not is_loading)
        self.check_button.setEnabled(not is_loading)
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

    def _append_message(self, sender, message, color):
        """Appends a formatted message to the chat display."""
        self.chat_display.append(f"<p style='color:{color};'>{sender}: {message}</p>")

    # --- Core Logic Methods ---

    def _start_course_check(self):
        """Handles the 'Check Course' button click."""
        url = self.url_input.text().strip()
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "لینک نامعتبر", "لطفاً یک لینک معتبر با http:// یا https:// وارد کنید.")
            return

        self.reset_chat()
        self._append_message("شما", f"در حال پردازش دوره از لینک: {url}", "#E0E0E0")
        self._set_ui_loading(True, "در حال استخراج محتوای دوره...")

        self._run_in_thread(self._scrape_course_content, url, self._on_scraping_complete)

    def _on_scraping_complete(self, result):
        """Callback for when web scraping is finished."""
        course_title, course_content = result
        self._append_message("سیستم", f"محتوای دوره '{course_title}' با موفقیت استخراج شد.", "#888")
        self.chat_display.append("<hr>")

        # Prepare the first message for the AI
        initial_user_message = f"محتوای دوره برای تحلیل:\nعنوان: {course_title}\nمحتوا: {course_content}"
        self.chat_history.append({'role': 'user', 'content': initial_user_message})

        self._set_ui_loading(True, "در حال دریافت پاسخ از استاد هوشمند...")
        self._run_in_thread(self._get_ai_response, self.chat_history, self._on_ai_complete)

    def _send_user_reply(self):
        """Handles sending the user's typed reply to the AI."""
        reply = self.user_input.text().strip()
        if not reply:
            return

        self._append_message("شما", reply, "#E0E0E0")
        self.user_input.clear()
        self.chat_history.append({'role': 'user', 'content': reply})

        self._set_ui_loading(True, "در حال دریافت پاسخ از استاد هوشمند...")
        self._run_in_thread(self._get_ai_response, self.chat_history, self._on_ai_complete)

    def _on_ai_complete(self, ai_response):
        """Callback for when the AI API call is finished."""
        cleaned_response = self._clean_ai_response(ai_response)
        self.chat_history.append({'role': 'assistant', 'content': cleaned_response})
        self._append_message("استاد هوشمند", cleaned_response, "#60A0FF")
        self._set_ui_loading(False)
        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.user_input.setFocus()

    def _on_task_error(self, error_message):
        """Callback for handling errors from the worker thread."""
        self._append_message("خطا", error_message, "#FF4040")
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

    def _get_ai_response(self, history):
        """Calls the LLM API and returns the response."""
        try:
            together.api_key = API_KEY
            response = together.Chat.create(
                model="deepseek-ai/deepseek-llm-67b-chat",
                messages=history,
                max_tokens=1024,
                temperature=0.7,
                top_p=0.9,
            )
            return response.choices[0].message.content
        except Exception as e:
            # Catch potential API errors from the 'together' library
            raise ConnectionError(f"خطا در ارتباط با هوش مصنوعی: {e}")

    def _clean_ai_response(self, text):
        """
        Cleans the AI's raw response to remove meta-commentary, thoughts,
        and other non-conversational artifacts.
        """
        # Remove any potential XML-like tags used for thinking
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

        # Clean up thread and worker after they're done
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

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
