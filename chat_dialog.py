import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QListWidget,
    QLineEdit, QPushButton, QHBoxLayout, QWidget
)

class ChatDialog(QDialog):
    """A mock-up dialog for a course's social group chat."""
    def __init__(self, course_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Social Group: {course_name}")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #E0E0E0; }
            QListWidget { border: 1px solid #4A4A4A; padding: 5px; font-size: 14px; }
            QLineEdit { border: 1px solid #4A4A4A; padding: 8px; font-size: 14px; }
            QPushButton { background-color: #4A4A4A; color: white; padding: 8px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #6E6E6E; }
        """)

        layout = QVBoxLayout(self)

        # Chat history
        self.chat_history = QListWidget()
        self.chat_history.addItem("User123: Has anyone finished Chapter 2?")
        self.chat_history.addItem("You: I'm working on it now.")
        self.chat_history.addItem("MentorBot: Remember to check the supplemental docs for Chapter 2!")
        layout.addWidget(self.chat_history)

        # Input area
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 5, 0, 0)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self.send_message) # Allow sending with Enter key
        input_layout.addWidget(self.message_input)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)

        layout.addWidget(input_widget)

    def send_message(self):
        """Adds the user's message to the chat history."""
        message = self.message_input.text()
        if message:
            self.chat_history.addItem(f"You: {message}")
            self.message_input.clear()
            self.chat_history.scrollToBottom()

# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = ChatDialog("Intro to Python")
    dialog.exec()
