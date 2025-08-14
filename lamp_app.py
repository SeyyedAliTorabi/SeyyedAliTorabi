import sys
import math
import random
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QStatusBar,
    QToolTip
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QRadialGradient, QPolygonF, QPainterPath, QLinearGradient
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSizeF, QTimer
from course_dialog import CourseDialog
from chat_dialog import ChatDialog

class GalacticWidget(QWidget):
    """Custom widget for drawing the galactic learning path."""
    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)

        self.courses = [
            {
                "id": "course_1", "name": "Intro to Python", "progress": 0.1,
                "completion_status": "not_started", # not_started, in_progress, completed
                "lessons": [
                    {"name": "Chapter 1: Basic Syntax", "completed": False},
                    {"name": "Chapter 2: Data Types", "completed": False},
                    {"name": "Chapter 3: Control Flow", "completed": False},
                ]
            },
            {
                "id": "course_2", "name": "Data Structures", "progress": 0.3,
                "completion_status": "not_started",
                "lessons": [
                    {"name": "Topic 1: Arrays & Lists", "completed": False},
                    {"name": "Topic 2: Stacks & Queues", "completed": False},
                ]
            },
            {
                "id": "course_3", "name": "Algorithms", "progress": 0.5,
                "completion_status": "not_started",
                "lessons": [
                    {"name": "Part 1: Sorting Algorithms", "completed": False},
                    {"name": "Part 2: Searching Algorithms", "completed": False},
                    {"name": "Part 3: Algorithmic Complexity", "completed": False},
                ]
            },
            {
                "id": "course_4", "name": "Machine Learning", "progress": 0.75,
                "completion_status": "not_started",
                "lessons": [
                    {"name": "Intro to ML", "completed": False},
                    {"name": "Supervised Learning", "completed": False},
                    {"name": "Unsupervised Learning", "completed": False},
                ]
            },
            {
                "id": "course_5", "name": "Advanced AI", "progress": 0.9,
                "completion_status": "not_started",
                "lessons": [
                    {"name": "Neural Networks", "completed": False},
                    {"name": "Deep Learning", "completed": False},
                ]
            },
        ]
        # Add animation state to each course
        for course in self.courses:
            course['moon_angle'] = random.uniform(0, 2 * math.pi)
            course['is_paused'] = False

        self.spiral_points = []
        self.interactive_items = []
        self.hovered_item_id = None
        self.user_progress = 0.6
        self.stars = []
        self._generate_stars(300, 1000)

        # Global animation timer
        self.animation_time = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)

        # State for final completion effect
        self.is_lamp_on = False
        self.is_final_effect_active = False
        self.effect_progress = 0.0
        self.layer_rotation_angle = 0.0

    def _generate_stars(self, num_stars, max_radius):
        """Generates a list of stars with random positions and twinkle properties."""
        for _ in range(num_stars):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, max_radius)
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            self.stars.append({
                'pos': QPointF(x, y),
                'base_alpha': random.randint(20, 90),
                'current_alpha': 0,
                'speed': random.uniform(0.01, 0.03),
                'offset': random.uniform(0, 2 * math.pi)
            })

    def _update_animation(self):
        """Updates animation state for moons and stars."""
        self.animation_time += 1
        # Update moon angles
        for course in self.courses:
            if not course.get('is_paused', False):
                course['moon_angle'] += 0.03
                if course['moon_angle'] > 2 * math.pi:
                    course['moon_angle'] -= 2 * math.pi
        # Update star twinkle
        for star in self.stars:
            amplitude = star['base_alpha'] / 2
            pulsation = math.sin(self.animation_time * star['speed'] + star['offset']) * amplitude
            star['current_alpha'] = star['base_alpha'] + pulsation

        # Update layer rotation
        self.layer_rotation_angle += 0.001

        # Update final effect animation
        if self.is_final_effect_active:
            self.effect_progress += 0.005  # Speed of the effect
            if self.effect_progress >= 1.0:
                self.effect_progress = 1.0
                self.is_final_effect_active = False
                self.is_lamp_on = True

        self.update()

    def resizeEvent(self, event):
        self._generate_spiral_points()
        super().resizeEvent(event)

    def paintEvent(self, event):
        if not self.spiral_points:
            self._generate_spiral_points()

        self.interactive_items.clear()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)

        self._draw_starfield(painter)
        self._draw_galactic_layers(painter)
        self._draw_spiral_path(painter)
        self._draw_planets_and_moons(painter)
        self._draw_expertise_lamp(painter)
        self._draw_completion_effect(painter)

    def mouseMoveEvent(self, event):
        painter_pos = event.position() - QPointF(self.width() / 2, self.height() / 2)
        new_hovered_id = None
        for item in reversed(self.interactive_items):
            if item['rect'].contains(painter_pos):
                new_hovered_id = item['id']
                break

        # Determine which planet is being hovered over (directly or via its moons)
        hovered_planet_id = None
        if new_hovered_id:
            if 'course' in new_hovered_id:
                hovered_planet_id = new_hovered_id
            else: # It's a moon
                hovered_planet_id = "_".join(new_hovered_id.split('_')[1:])

        # Update the pause state for each course
        for course in self.courses:
            course['is_paused'] = (course['id'] == hovered_planet_id)

        # Update visual hover effect for the specific item
        if self.hovered_item_id != new_hovered_id:
            self.hovered_item_id = new_hovered_id
            if new_hovered_id is None:
                QToolTip.hideText()
            else:
                item_type = next((item['type'] for item in self.interactive_items if item['id'] == new_hovered_id), "")
                if 'course' in item_type:
                    item_name = next((c['name'] for c in self.courses if c['id'] == new_hovered_id), "")
                    tooltip_text = f"Course: {item_name}"
                elif 'social' in item_type:
                    tooltip_text = "Social Group"
                else:
                    tooltip_text = "Mentoring"
                QToolTip.showText(self.mapToGlobal(event.position().toPoint()), tooltip_text, self)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            painter_pos = event.position() - QPointF(self.width() / 2, self.height() / 2)
            for item in reversed(self.interactive_items):
                if item['rect'].contains(painter_pos):
                    self.itemClicked.emit(item['id'])
                    break

    def _draw_completion_effect(self, painter):
        """Draws a light pulse traveling along the spiral."""
        if not self.is_final_effect_active or not self.spiral_points:
            return

        painter.save()

        progress_index = int((len(self.spiral_points) - 1) * self.effect_progress)
        pos = self.spiral_points[progress_index]

        radius = 20
        gradient = QRadialGradient(pos, radius)
        gradient.setColorAt(0, QColor(255, 255, 255, 255))
        gradient.setColorAt(0.5, QColor(255, 255, 100, 150))
        gradient.setColorAt(1, QColor(255, 255, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(pos, radius, radius)

        painter.restore()

    def _check_for_full_completion(self):
        """Checks if all courses are completed and triggers the final effect."""
        if self.is_final_effect_active or self.is_lamp_on:
            return

        all_done = all(course.get('completion_status') == 'completed' for course in self.courses)

        if all_done:
            print("All courses completed! Starting final effect...")
            self.is_final_effect_active = True
            self.effect_progress = 0.0

    def update_course_data(self, updated_data):
        """Finds the course by ID and updates its data and completion status."""
        course_id = updated_data.get('id')
        if not course_id:
            return

        for i, course in enumerate(self.courses):
            if course['id'] == course_id:
                self.courses[i]['lessons'] = updated_data['lessons']

                completed_lessons = sum(1 for lesson in self.courses[i]['lessons'] if lesson['completed'])
                total_lessons = len(self.courses[i]['lessons'])

                if total_lessons == 0:
                    status = 'not_started'
                elif completed_lessons == total_lessons:
                    status = 'completed'
                elif completed_lessons > 0:
                    status = 'in_progress'
                else:
                    status = 'not_started'

                self.courses[i]['completion_status'] = status
                self.update() # Repaint to show visual feedback
                self._check_for_full_completion()
                break

    def _draw_starfield(self, painter):
        """Draws the twinkling starfield background."""
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for star in self.stars:
            painter.setBrush(QColor(255, 255, 255, int(star['current_alpha'])))
            painter.drawEllipse(star['pos'], 1, 1)
        painter.restore()

    def _draw_expertise_lamp(self, painter):
        """Draws a compact, stylized lamp centered at the origin."""
        painter.save()

        lamp_height = 40
        shade_top_width = 30
        shade_bottom_width = 50

        # Glow effect (drawn first to be in the back)
        if self.is_lamp_on:
            glow_center = QPointF(0, 0)
            glow_radius = shade_bottom_width * 1.2
            gradient = QRadialGradient(glow_center, glow_radius)
            gradient.setColorAt(0, QColor(255, 255, 224, 180))
            gradient.setColorAt(0.8, QColor(255, 220, 100, 40))
            gradient.setColorAt(1, QColor(13, 17, 23, 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(glow_center, glow_radius, glow_radius)

        # Lampshade shape
        path = QPainterPath()
        path.moveTo(-shade_top_width / 2, -lamp_height)
        path.lineTo(-shade_bottom_width / 2, 0)
        path.arcTo(QRectF(-shade_bottom_width / 2, -5, shade_bottom_width, 10), 180, -180)
        path.lineTo(shade_top_width / 2, -lamp_height)
        path.closeSubpath()

        shade_gradient = QLinearGradient(0, -lamp_height, 0, 0)
        shade_gradient.setColorAt(0, QColor("#AAAAAA"))
        shade_gradient.setColorAt(1, QColor("#666666"))
        painter.setBrush(shade_gradient)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawPath(path)

        # Text "Expertise" below the lamp
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Roboto", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(-50, 10, 100, 20), Qt.AlignmentFlag.AlignCenter, "Expertise")

        painter.restore()

    def _generate_spiral_points(self):
        start_radius = min(self.width(), self.height()) / 2 * 0.85
        if start_radius <= 0:
            self.spiral_points = []
            return
        a, b, theta_max = start_radius, 0.15, 4.5 * math.pi
        num_steps = 500
        points = []
        for i in range(num_steps + 1):
            theta = (theta_max / num_steps) * i
            r = a * math.exp(-b * theta)
            angle = theta - math.pi / 2
            points.append(QPointF(r * math.cos(angle), r * math.sin(angle)))
        self.spiral_points = points

    def _draw_spiral_path(self, painter):
        painter.save()
        if not self.spiral_points:
            painter.restore()
            return

        # Define two sets of colors for the gradient
        uncompleted_start_color, uncompleted_end_color = QColor("#8A2BE2"), QColor("#FF8C00")
        completed_start_color, completed_end_color = QColor("#A992F5"), QColor("#FFB74D")

        pen = QPen()
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        progress_index = int((len(self.spiral_points) - 1) * self.user_progress)

        # Draw the completed part of the path
        for i in range(progress_index):
            progress = i / (len(self.spiral_points) - 1)
            r = int(completed_start_color.red() + (completed_end_color.red() - completed_start_color.red()) * progress)
            g = int(completed_start_color.green() + (completed_end_color.green() - completed_start_color.green()) * progress)
            b = int(completed_start_color.blue() + (completed_end_color.blue() - completed_start_color.blue()) * progress)
            pen.setColor(QColor(r, g, b))
            painter.setPen(pen)
            painter.drawLine(self.spiral_points[i], self.spiral_points[i+1])

        # Draw the uncompleted part of the path
        for i in range(progress_index, len(self.spiral_points) - 1):
            progress = i / (len(self.spiral_points) - 1)
            r = int(uncompleted_start_color.red() + (uncompleted_end_color.red() - uncompleted_start_color.red()) * progress)
            g = int(uncompleted_start_color.green() + (uncompleted_end_color.green() - uncompleted_start_color.green()) * progress)
            b = int(uncompleted_start_color.blue() + (uncompleted_end_color.blue() - uncompleted_start_color.blue()) * progress)
            pen.setColor(QColor(r, g, b))
            painter.setPen(pen)
            painter.drawLine(self.spiral_points[i], self.spiral_points[i+1])

        start_point = self.spiral_points[0]
        painter.setPen(QColor(Qt.GlobalColor.white))
        painter.setFont(QFont("Roboto", 10))
        painter.drawText(int(start_point.x()), int(start_point.y()) - 20, "Start")
        painter.restore()

    def _draw_planets_and_moons(self, painter):
        painter.save()
        if not self.spiral_points:
            painter.restore()
            return

        base_planet_radius, base_moon_radius, moon_orbit_radius = 14, 6, 22

        for course in self.courses:
            point_index = int(course["progress"] * (len(self.spiral_points) - 1))
            planet_pos = self.spiral_points[point_index]

            # --- Planet ---
            is_hovered = (course['id'] == self.hovered_item_id)
            planet_radius = base_planet_radius * 1.5 if is_hovered else base_planet_radius
            painter.setBrush(QColor("#a29bfe"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(planet_pos, planet_radius, planet_radius)

            # --- Add visual feedback for completion status ---
            status = course.get('completion_status', 'not_started')
            if status == 'in_progress':
                painter.save()
                pen = QPen(QColor(255, 255, 0, 150))
                pulse = (math.sin(self.animation_time * 0.1) + 1) / 2
                pen.setWidth(int(2 + pulse * 2))
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(planet_pos, planet_radius, planet_radius)
                painter.restore()
            elif status == 'completed':
                painter.save()
                pen = QPen(QColor(0, 255, 127, 200))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(planet_pos, planet_radius + 3, planet_radius + 3)
                painter.restore()

            planet_rect = QRectF(planet_pos - QPointF(planet_radius, planet_radius), QSizeF(planet_radius*2, planet_radius*2))
            self.interactive_items.append({"id": course['id'], "name": course['name'], "rect": planet_rect, "type": "course_planet"})

            # --- Moons ---
            social_id = f"social_{course['id']}"
            is_social_hovered = (social_id == self.hovered_item_id)
            social_radius = base_moon_radius * 1.5 if is_social_hovered else base_moon_radius
            moon1_angle = course['moon_angle']
            moon1_pos = QPointF(planet_pos.x() + moon_orbit_radius * math.cos(moon1_angle), planet_pos.y() + moon_orbit_radius * math.sin(moon1_angle))
            painter.setBrush(QColor("#55efc4"))
            painter.drawEllipse(moon1_pos, social_radius, social_radius)

            # Draw a simple person icon on the social moon
            painter.save()
            icon_pen = QPen(QColor("#006266"))
            icon_pen.setWidthF(0.8)
            painter.setPen(icon_pen)
            # Head
            head_radius = social_radius * 0.3
            head_center = QPointF(moon1_pos.x(), moon1_pos.y() - social_radius * 0.25)
            painter.drawEllipse(head_center, head_radius, head_radius)
            # Body
            body_rect = QRectF(head_center.x() - head_radius * 1.5, head_center.y() + head_radius * 0.5, head_radius * 3, head_radius * 2)
            painter.drawArc(body_rect, -30 * 16, -120 * 16)
            painter.restore()

            social_rect = QRectF(moon1_pos - QPointF(social_radius, social_radius), QSizeF(social_radius*2, social_radius*2))
            self.interactive_items.append({"id": social_id, "rect": social_rect, "type": "moon_social"})

            mentor_id = f"mentor_{course['id']}"
            is_mentor_hovered = (mentor_id == self.hovered_item_id)
            mentor_radius = base_moon_radius * 1.5 if is_mentor_hovered else base_moon_radius
            moon2_angle = course['moon_angle'] + math.pi
            moon2_pos = QPointF(planet_pos.x() + moon_orbit_radius * math.cos(moon2_angle), planet_pos.y() + moon_orbit_radius * math.sin(moon2_angle))
            star = QPolygonF()
            for i in range(10):
                radius = mentor_radius if i % 2 == 0 else mentor_radius / 2.5
                angle = i * math.pi / 5 - math.pi / 2
                star.append(QPointF(moon2_pos.x() + radius * math.cos(angle), moon2_pos.y() + radius * math.sin(angle)))
            painter.setBrush(QColor("#ffeaa7"))
            painter.drawPolygon(star)
            self.interactive_items.append({"id": mentor_id, "rect": star.boundingRect(), "type": "moon_mentor"})

        painter.restore()

    def _draw_galactic_layers(self, painter):
        painter.save()
        pen = QPen(QColor("#4a90e2"))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        max_radius = min(self.width(), self.height()) / 2 * 0.9
        num_orbits = 5
        for i in range(1, num_orbits + 1):
            painter.save()
            radius = max_radius * (i / num_orbits)
            # Rotate each layer at a different speed for a parallax effect
            rotation_speed_multiplier = (num_orbits - i + 1) * 0.5
            painter.rotate(math.degrees(self.layer_rotation_angle * rotation_speed_multiplier))
            painter.setPen(pen)
            painter.drawEllipse(int(-radius), int(-radius), int(radius * 2), int(radius * 2))
            painter.restore()

        painter.restore()

from PyQt6.QtWidgets import QVBoxLayout

class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lamp: The Galactic Learning Path")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color: #0d1117; color: white;")

        # Main container widget and layout
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # Title Label
        title_label = QLabel("The Galactic Learning Path")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #E0E0E0; padding-bottom: 10px;")
        layout.addWidget(title_label)

        # Galactic Widget
        self.galactic_widget = GalacticWidget(self)
        layout.addWidget(self.galactic_widget)

        self.setCentralWidget(container)
        self.galactic_widget.itemClicked.connect(self.on_item_clicked)

        # Status Bar (without slogan)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("background-color: #161b22;")

    def on_item_clicked(self, item_id):
        """Handles the click event from the galactic widget."""
        item_type = ""
        for item in self.galactic_widget.interactive_items:
            if item['id'] == item_id:
                item_type = item.get('type', "")
                break

        if 'course' in item_type:
            course_data = next((c for c in self.galactic_widget.courses if c['id'] == item_id), None)
            if course_data:
                dialog = CourseDialog(course_data, self)
                dialog.courseUpdated.connect(self.galactic_widget.update_course_data)
                dialog.exec()
        elif 'social' in item_type:
            course_id = "_".join(item_id.split('_')[1:])
            course_name = next((c['name'] for c in self.galactic_widget.courses if c['id'] == course_id), "Unknown Course")
            dialog = ChatDialog(course_name, self)
            dialog.exec()
        else: # Handle mentor moon clicks
            message = f"Clicked on: Mentoring"
            self.status_bar.showMessage(message, 3000)
            print(message)

def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
