import sys
import math
import random
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QStatusBar,
    QToolTip,
    QVBoxLayout
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

        # Inverted progress: Lower progress is now closer to the center (start of the spiral)
        self.courses = [
            {
                "id": "course_1", "name": "Intro to Python", "progress": 0.1,
                "light_required": 0.0, # Visible from the start
                "lessons": [
                    {"name": "Chapter 1: Basic Syntax", "completed": False},
                    {"name": "Chapter 2: Data Types", "completed": False},
                    {"name": "Chapter 3: Control Flow", "completed": False},
                ]
            },
            {
                "id": "course_2", "name": "Data Structures", "progress": 0.25,
                "light_required": 0.1, # Requires 10% total completion
                "lessons": [
                    {"name": "Topic 1: Arrays & Lists", "completed": False},
                    {"name": "Topic 2: Stacks & Queues", "completed": False},
                ]
            },
            {
                "id": "course_3", "name": "Algorithms", "progress": 0.45,
                "light_required": 0.25, # Requires 25% total completion
                "lessons": [
                    {"name": "Part 1: Sorting Algorithms", "completed": False},
                    {"name": "Part 2: Searching Algorithms", "completed": False},
                    {"name": "Part 3: Algorithmic Complexity", "completed": False},
                ]
            },
            {
                "id": "course_4", "name": "Machine Learning", "progress": 0.65,
                "light_required": 0.5, # Requires 50% total completion
                "lessons": [
                    {"name": "Intro to ML", "completed": False},
                    {"name": "Supervised Learning", "completed": False},
                    {"name": "Unsupervised Learning", "completed": False},
                ]
            },
            {
                "id": "course_5", "name": "Advanced AI", "progress": 0.85,
                "light_required": 0.75, # Requires 75% total completion
                "lessons": [
                    {"name": "Neural Networks", "completed": False},
                    {"name": "Deep Learning", "completed": False},
                ]
            },
        ]
        # Add animation and completion state to each course
        for course in self.courses:
            course['moon_angle'] = random.uniform(0, 2 * math.pi)
            course['is_paused'] = False
            course['completion_status'] = 'not_started'

        self.spiral_points = []
        self.interactive_items = []
        self.hovered_item_id = None
        self.stars = []
        self._generate_stars(300, 1000)

        # Light-based properties for Fog of War
        self.lamp_brightness = 0.0 # Overall progress, from 0.0 to 1.0
        self._calculate_lamp_brightness() # Initial calculation

        # Animation timer
        self.animation_time = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)
        self.layer_rotation_angle = 0.0

        # State for final blink effect
        self.is_fully_complete = False
        self.blink_cycle_time = 0

    def _generate_stars(self, num_stars, max_radius):
        """Generates a list of stars with random positions and twinkle properties."""
        for _ in range(num_stars):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, max_radius)
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            self.stars.append({
                'pos': QPointF(x, y),
                'base_alpha': random.randint(40, 140),  # Increased brightness
                'current_alpha': 0,
                'speed': random.uniform(0.02, 0.05),   # Increased speed
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
            # Make pulsation more pronounced
            amplitude = star['base_alpha'] * 0.8
            pulsation = math.sin(self.animation_time * star['speed'] + star['offset']) * amplitude
            # Clamp the alpha value between 0 and 255
            star['current_alpha'] = max(0, min(255, star['base_alpha'] + pulsation))

        # Update layer rotation
        self.layer_rotation_angle += 0.001

        # Update final blink effect
        if self.is_fully_complete:
            self.blink_cycle_time = (self.blink_cycle_time + 1) % 100 # ~3 second cycle

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

    def _calculate_lamp_brightness(self):
        """Calculates the total progress across all lessons."""
        total_lessons = 0
        completed_lessons = 0
        for course in self.courses:
            total_lessons += len(course['lessons'])
            completed_lessons += sum(1 for lesson in course['lessons'] if lesson['completed'])

        if total_lessons == 0:
            self.lamp_brightness = 0.0
        else:
            self.lamp_brightness = completed_lessons / total_lessons

        print(f"Lamp brightness updated to: {self.lamp_brightness:.2f}")


    def update_course_data(self, updated_data):
        """Updates course data, recalculates brightness, and checks statuses."""
        course_id = updated_data.get('id')
        if not course_id:
            return

        for i, course in enumerate(self.courses):
            if course['id'] == course_id:
                self.courses[i]['lessons'] = updated_data['lessons']

                # Recalculate completion status for this specific course
                completed_count = sum(1 for lesson in self.courses[i]['lessons'] if lesson['completed'])
                total_count = len(self.courses[i]['lessons'])

                if total_count == 0: status = 'not_started'
                elif completed_count == total_count: status = 'completed'
                elif completed_count > 0: status = 'in_progress'
                else: status = 'not_started'
                self.courses[i]['completion_status'] = status

                # Recalculate overall lamp brightness
                self._calculate_lamp_brightness()

                # Check if all courses are complete
                if self.lamp_brightness >= 1.0:
                    self.is_fully_complete = True

                self.update()
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
        """Draws the central lamp, with appearance tied to brightness."""
        painter.save()
        center_radius = 40

        # Glow is proportional to brightness
        glow_radius = center_radius * (1 + self.lamp_brightness * 1.5)
        glow_alpha = int(50 + self.lamp_brightness * 150)

        # Add blink effect on full completion
        if self.is_fully_complete:
            # A pulse that goes from 0 to 1 and back to 0 over the cycle time
            pulse = abs(50 - self.blink_cycle_time) / 50.0 # Creates a dip in the middle
            glow_alpha = int(glow_alpha * (0.6 + 0.4 * pulse)) # Modulate alpha
            glow_radius = glow_radius * (0.8 + 0.2 * pulse) # Modulate radius


        glow_gradient = QRadialGradient(0, 0, glow_radius)
        glow_gradient.setColorAt(0, QColor(255, 255, 224, glow_alpha))
        glow_gradient.setColorAt(1, QColor(13, 17, 23, 0))
        painter.setBrush(glow_gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, 0), glow_radius, glow_radius)

        # Base of the lamp
        painter.setBrush(QColor(80, 80, 90, 100))
        painter.setPen(QPen(QColor(120, 120, 130)))
        painter.drawEllipse(QPointF(0, 0), center_radius, center_radius)

        # Filament brightness
        filament_color = QColor.fromHsvF(0.15, 0.8, 0.5 + self.lamp_brightness * 0.5, 1.0)
        filament_pen = QPen(filament_color)
        filament_pen.setWidth(int(1 + self.lamp_brightness * 2))
        painter.setPen(filament_pen)
        path = QPainterPath()
        path.moveTo(-8, 0)
        path.cubicTo(QPointF(-4, -8), QPointF(4, 8), QPointF(8, 0))
        painter.drawPath(path)

        # Text
        text_rect = QRectF(-center_radius, -center_radius, center_radius * 2, center_radius * 2)
        font = QFont("Roboto", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0, 150))
        painter.drawText(text_rect.translated(1, 1), Qt.AlignmentFlag.AlignCenter, "Expertise")
        painter.setPen(QColor("#FFFFFF"))
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

        points.reverse() # Reverse the points to spiral outwards
        self.spiral_points = points

    def _draw_spiral_path(self, painter):
        """Draws the spiral path, revealing it based on lamp brightness."""
        painter.save()
        if not self.spiral_points:
            painter.restore()
            return

        pen = QPen()
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # Find the maximum progress of a visible course
        max_visible_progress = 0.0
        for course in self.courses:
            if self.lamp_brightness >= course['light_required']:
                max_visible_progress = max(max_visible_progress, course['progress'])

        # The length of the visible path is determined by the furthest visible planet
        visible_path_length = int((len(self.spiral_points) - 1) * max_visible_progress)

        # Gradient colors (now warm to cold for outward spiral)
        start_color, end_color = QColor("#FF8C00"), QColor("#8A2BE2")

        for i in range(visible_path_length):
            segment_progress = (i + 1) / (len(self.spiral_points) - 1)

            target_course = None
            for c in sorted(self.courses, key=lambda x: x['progress']):
                if segment_progress <= c['progress']:
                    target_course = c
                    break
            if not target_course:
                 target_course = self.courses[-1]

            light_needed = target_course['light_required']
            alpha = 0
            if self.lamp_brightness >= light_needed:
                excess_light = self.lamp_brightness - light_needed
                alpha = int(min(1.0, excess_light / 0.1) * 255)

            progress_ratio = i / (len(self.spiral_points) - 1)
            r = int(start_color.red() + (end_color.red() - start_color.red()) * progress_ratio)
            g = int(start_color.green() + (end_color.green() - start_color.green()) * progress_ratio)
            b = int(start_color.blue() + (end_color.blue() - start_color.blue()) * progress_ratio)

            pen.setColor(QColor(r, g, b, alpha))
            painter.setPen(pen)
            painter.drawLine(self.spiral_points[i], self.spiral_points[i+1])

        start_point = self.spiral_points[0]
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Roboto", 10))
        painter.drawText(int(start_point.x() + 15), int(start_point.y()), "Start")
        painter.restore()

    def _draw_planets_and_moons(self, painter):
        painter.save()
        if not self.spiral_points:
            painter.restore()
            return

        base_planet_radius, base_moon_radius, moon_orbit_radius = 14, 6, 22

        for course in self.courses:
            light_needed = course['light_required']
            if self.lamp_brightness < light_needed:
                continue

            excess_light = self.lamp_brightness - light_needed
            alpha = int(min(1.0, excess_light / 0.1) * 255)

            point_index = int(course["progress"] * (len(self.spiral_points) - 1))
            planet_pos = self.spiral_points[point_index]

            is_hovered = (course['id'] == self.hovered_item_id)
            planet_radius = base_planet_radius * 1.5 if is_hovered else base_planet_radius

            planet_color = QColor("#a29bfe")
            planet_color.setAlpha(alpha)
            painter.setBrush(planet_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(planet_pos, planet_radius, planet_radius)

            status = course.get('completion_status', 'not_started')
            if status == 'in_progress' or status == 'completed':
                ring_color = QColor(255, 255, 0) if status == 'in_progress' else QColor(0, 255, 127)
                ring_color.setAlpha(alpha)
                painter.save()
                pen = QPen(ring_color)
                if status == 'in_progress':
                    pulse = (math.sin(self.animation_time * 0.1) + 1) / 2
                    pen.setWidth(int(2 + pulse * 2))
                else:
                    pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(planet_pos, planet_radius + (3 if status=='completed' else 0), planet_radius + (3 if status=='completed' else 0))
                painter.restore()

            planet_rect = QRectF(planet_pos - QPointF(planet_radius, planet_radius), QSizeF(planet_radius*2, planet_radius*2))
            self.interactive_items.append({"id": course['id'], "name": course['name'], "rect": planet_rect, "type": "course_planet"})

            # --- Moons ---
            social_id = f"social_{course['id']}"
            is_social_hovered = (social_id == self.hovered_item_id)
            social_radius = base_moon_radius * 1.5 if is_social_hovered else base_moon_radius
            moon1_angle = course['moon_angle']
            moon1_pos = QPointF(planet_pos.x() + moon_orbit_radius * math.cos(moon1_angle), planet_pos.y() + moon_orbit_radius * math.sin(moon1_angle))
            social_color = QColor("#55efc4")
            social_color.setAlpha(alpha)
            painter.setBrush(social_color)
            painter.drawEllipse(moon1_pos, social_radius, social_radius)

            icon_pen = QPen(QColor(0, 98, 102, alpha))
            icon_pen.setWidthF(0.8)
            painter.setPen(icon_pen)
            head_radius = social_radius * 0.3
            head_center = QPointF(moon1_pos.x(), moon1_pos.y() - social_radius * 0.25)
            painter.drawEllipse(head_center, head_radius, head_radius)
            body_rect = QRectF(head_center.x() - head_radius * 1.5, head_center.y() + head_radius * 0.5, head_radius * 3, head_radius * 2)
            painter.drawArc(body_rect, -30 * 16, -120 * 16)

            social_rect = QRectF(moon1_pos - QPointF(social_radius, social_radius), QSizeF(social_radius*2, social_radius*2))
            self.interactive_items.append({"id": social_id, "rect": social_rect, "type": "moon_social"})

            mentor_id = f"mentor_{course['id']}"
            is_mentor_hovered = (mentor_id == self.hovered_item_id)
            mentor_radius = base_moon_radius * 1.5 if is_mentor_hovered else base_moon_radius
            moon2_angle = course['moon_angle'] + math.pi
            moon2_pos = QPointF(planet_pos.x() + moon_orbit_radius * math.cos(moon2_angle), planet_pos.y() + moon_orbit_radius * math.sin(moon2_angle))

            mentor_color = QColor("#ffeaa7")
            mentor_color.setAlpha(alpha)
            painter.setBrush(mentor_color)
            painter.setPen(Qt.PenStyle.NoPen)

            star = QPolygonF()
            for i in range(10):
                radius = mentor_radius if i % 2 == 0 else mentor_radius / 2.5
                angle = i * math.pi / 5 - math.pi / 2
                star.append(QPointF(moon2_pos.x() + radius * math.cos(angle), moon2_pos.y() + radius * math.sin(angle)))
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
