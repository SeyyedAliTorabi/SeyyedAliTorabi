import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QCheckBox,
    QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, Qt

class CourseDialog(QDialog):
    """A dialog to display and edit the lessons of a course."""
    # Signal emitted when the dialog is accepted, carrying the updated course data
    courseUpdated = pyqtSignal(dict)

    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        # Store a deep copy of the data to modify safely
        self.course_data = course_data.copy()
        self.course_data['lessons'] = [lesson.copy() for lesson in course_data['lessons']]

        self.setWindowTitle(f"Course Details: {self.course_data['name']}")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #161b22;
                color: #E0E0E0;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
            QCheckBox {
                font-size: 14px;
                spacing: 10px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6E6E6E;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel(f"Lessons for {self.course_data['name']}")
        layout.addWidget(title)

        self.checkboxes = []
        for i, lesson in enumerate(self.course_data['lessons']):
            checkbox = QCheckBox(lesson['name'])
            checkbox.setChecked(lesson['completed'])
            checkbox.stateChanged.connect(lambda state, index=i: self._lesson_state_changed(index, state))
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _lesson_state_changed(self, index, state):
        """Updates the lesson's completed status when a checkbox is toggled."""
        self.course_data['lessons'][index]['completed'] = (state == Qt.CheckState.Checked.value)

    def accept(self):
        """Emits the signal with updated data and closes the dialog."""
        self.courseUpdated.emit(self.course_data)
        super().accept()

# Example usage for testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    sample_course = {
        "id": "course_1", "name": "Intro to Python",
        "lessons": [
            {"name": "Chapter 1: Basic Syntax", "completed": False},
            {"name": "Chapter 2: Data Types", "completed": True},
            {"name": "Chapter 3: Control Flow", "completed": False},
        ]
    }
    dialog = CourseDialog(sample_course)
    dialog.courseUpdated.connect(lambda data: print("Updated data:", data))
    dialog.exec()
