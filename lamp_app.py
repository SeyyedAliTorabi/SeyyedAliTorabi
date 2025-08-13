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
    QPainter, QColor, QBrush, QPen, QFont, QRadialGradient, QPolygonF
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSizeF, QTimer

# Slogan in Persian
SLOGAN = "مسیرت روشن، تخصصت بی‌نکران"

class GalacticWidget(QWidget):
    """Custom widget for drawing the galactic learning path."""
    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)

        self.courses = [
            {"id": "course_1", "name": "Intro to Python", "progress": 0.1},
            {"id": "course_2", "name": "Data Structures", "progress": 0.3},
            {"id": "course_3", "name": "Algorithms", "progress": 0.5},
            {"id": "course_4", "name": "Machine Learning", "progress": 0.75},
            {"id": "course_5", "name": "Advanced AI", "progress": 0.9},
        ]
        self.spiral_points = []
        self.interactive_items = []
        self.hovered_item_id = None
        self.user_progress = 0.6  # 0.0 to 1.0, example value
        self.stars = []
        self._generate_stars(300, 1000)

        # For moon animation
        self.moon_animation_angle = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)  # ~30 FPS

    def _generate_stars(self, num_stars, max_radius):
        """Generates a list of stars with random positions and brightness."""
        for _ in range(num_stars):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, max_radius)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            brightness = random.randint(30, 120)
            self.stars.append((QPointF(x, y), brightness))

    def _update_animation(self):
        """Updates the animation angle and triggers a repaint."""
        self.moon_animation_angle += 0.03
        if self.moon_animation_angle > 2 * math.pi:
            self.moon_animation_angle -= 2 * math.pi
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

    def mouseMoveEvent(self, event):
        painter_pos = event.position() - QPointF(self.width() / 2, self.height() / 2)
        found_item = None
        for item in reversed(self.interactive_items):
            if item['rect'].contains(painter_pos):
                found_item = item
                break

        if found_item:
            # Pause animation when hovering
            if self.animation_timer.isActive():
                self.animation_timer.stop()

            if self.hovered_item_id != found_item['id']:
                self.hovered_item_id = found_item['id']
                if 'course' in found_item['type']:
                    tooltip_text = f"Course: {found_item['name']}"
                elif 'social' in found_item['type']:
                    tooltip_text = "Social Group"
                else:
                    tooltip_text = "Mentoring"
                QToolTip.showText(self.mapToGlobal(event.position().toPoint()), tooltip_text, self)
                self.update()
        else:
            # Resume animation when not hovering
            if not self.animation_timer.isActive():
                self.animation_timer.start(33)

            if self.hovered_item_id is not None:
                self.hovered_item_id = None
                QToolTip.hideText()
                self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            painter_pos = event.position() - QPointF(self.width() / 2, self.height() / 2)
            for item in reversed(self.interactive_items):
                if item['rect'].contains(painter_pos):
                    self.itemClicked.emit(item['id'])
                    break

    def _draw_starfield(self, painter):
        """Draws the starfield background."""
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for pos, brightness in self.stars:
            painter.setBrush(QColor(255, 255, 255, brightness))
            painter.drawEllipse(pos, 1, 1)
        painter.restore()

    def _draw_expertise_lamp(self, painter):
        """Draws the central 'Expertise Lamp'."""
        painter.save()

        bulb_center_y = -60
        bulb_radius = 25

        # 1. The Glow
        glow_radius = bulb_radius * 2.5
        gradient = QRadialGradient(0, bulb_center_y, glow_radius)
        gradient.setColorAt(0, QColor(255, 255, 224, 200))
        gradient.setColorAt(1, QColor(13, 17, 23, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, bulb_center_y), glow_radius, glow_radius)

        # 2. The Lamp Base
        base_width = 80
        base_height = 15
        painter.setBrush(QColor("#4F4F4F"))
        painter.drawRect(int(-base_width/2), 0, base_width, base_height)

        # 3. The Lamp Stand
        stand_width = 8
        stand_height = 60
        painter.setBrush(QColor("#6E6E6E"))
        painter.drawRect(int(-stand_width/2), -stand_height, stand_width, stand_height)

        # 4. The Bulb
        painter.setBrush(QColor("#FFFFE0"))
        painter.drawEllipse(QPointF(0, bulb_center_y), bulb_radius, bulb_radius)

        # 5. Text on the base
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Roboto", 10, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRectF(-base_width/2, 0, base_width, base_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Expertise")

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
            planet_rect = QRectF(planet_pos - QPointF(planet_radius, planet_radius), QSizeF(planet_radius*2, planet_radius*2))
            self.interactive_items.append({"id": course['id'], "name": course['name'], "rect": planet_rect, "type": "course_planet"})

            # --- Moons ---
            social_id = f"social_{course['id']}"
            is_social_hovered = (social_id == self.hovered_item_id)
            social_radius = base_moon_radius * 1.5 if is_social_hovered else base_moon_radius
            moon1_angle = self.moon_animation_angle
            moon1_pos = QPointF(planet_pos.x() + moon_orbit_radius * math.cos(moon1_angle), planet_pos.y() + moon_orbit_radius * math.sin(moon1_angle))
            painter.setBrush(QColor("#55efc4"))
            painter.drawEllipse(moon1_pos, social_radius, social_radius)
            social_rect = QRectF(moon1_pos - QPointF(social_radius, social_radius), QSizeF(social_radius*2, social_radius*2))
            self.interactive_items.append({"id": social_id, "rect": social_rect, "type": "moon_social"})

            mentor_id = f"mentor_{course['id']}"
            is_mentor_hovered = (mentor_id == self.hovered_item_id)
            mentor_radius = base_moon_radius * 1.5 if is_mentor_hovered else base_moon_radius
            moon2_angle = self.moon_animation_angle + math.pi
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
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        max_radius = min(self.width(), self.height()) / 2 * 0.9
        for i in range(1, 6):
            radius = max_radius * (i / 5)
            painter.drawEllipse(int(-radius), int(-radius), int(radius * 2), int(radius * 2))
        painter.restore()

class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lamp: The Galactic Learning Path")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color: #0d1117; color: white;")

        self.galactic_widget = GalacticWidget(self)
        self.setCentralWidget(self.galactic_widget)
        self.galactic_widget.itemClicked.connect(self.on_item_clicked)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        slogan_label = QLabel(SLOGAN)
        slogan_label.setStyleSheet("color: #aaaaaa; padding: 5px;")
        self.status_bar.addPermanentWidget(slogan_label)

    def on_item_clicked(self, item_id):
        """Handles the click event from the galactic widget."""
        item_name = "Unknown"
        for item in self.galactic_widget.interactive_items:
            if item['id'] == item_id:
                if 'course' in item['type']:
                    item_name = f"Course: {item['name']}"
                elif 'social' in item['type']:
                    item_name = "Social Group"
                else:
                    item_name = "Mentoring"
                break

        message = f"Clicked on: {item_name}"
        self.status_bar.showMessage(message, 3000) # Show for 3 seconds
        print(message)

def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
