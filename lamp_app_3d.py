import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer

import numpy as np
from OpenGL.GL import *
from PyQt6.QtGui import QOpenGLShaderProgram, QMatrix4x4, QVector3D
from PyQt6.QtOpenGL import QOpenGLBuffer, QOpenGLVertexArrayObject

class GalacticGLWidget(QOpenGLWidget):
    """Custom QOpenGLWidget for 3D visualization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gradient_shader = None
        self.solid_shader = None
        self.projection_matrix = QMatrix4x4()
        self.view_matrix = QMatrix4x4()

        # Data for spiral
        self.spiral_vbo = QOpenGLBuffer()
        self.spiral_vao = QOpenGLVertexArrayObject()
        self.spiral_vertex_count = 0
        self.spiral_path_points = []

        # Data for planets (unit sphere)
        self.sphere_vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self.sphere_ebo = QOpenGLBuffer(QOpenGLBuffer.Type.IndexBuffer)
        self.sphere_vao = QOpenGLVertexArrayObject()
        self.sphere_index_count = 0

        # Data for lamp (unit cube)
        self.cube_vbo = QOpenGLBuffer()
        self.cube_vao = QOpenGLVertexArrayObject()

        self.courses = [
            {"name": "Intro to Python", "progress": 0.1},
            {"name": "Data Structures", "progress": 0.3},
            {"name": "Algorithms", "progress": 0.5},
            {"name": "Machine Learning", "progress": 0.75},
            {"name": "Advanced AI", "progress": 0.9},
        ]

        # For moon animation
        self.moon_animation_angle = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)  # ~30 FPS

    def _generate_spiral_vertices(self):
        """Generates vertices for the 3D spiral path with a color gradient."""
        start_radius, z_amplitude = 400.0, 150.0
        a, b, theta_max = start_radius, 0.15, 4.5 * np.pi
        num_steps = 1000
        start_color = np.array([0.54, 0.17, 0.89])
        end_color = np.array([1.00, 0.55, 0.00])
        vertices = []
        self.spiral_path_points = []
        for i in range(num_steps + 1):
            progress = i / num_steps
            theta = progress * theta_max
            r = a * np.exp(-b * theta)
            angle = theta - np.pi / 2
            x, y = r * np.cos(angle), r * np.sin(angle)
            z = -z_amplitude * np.sin(progress * np.pi)
            self.spiral_path_points.append(QVector3D(x, y, z))
            color = start_color + (end_color - start_color) * progress
            vertices.extend([x, y, z, color[0], color[1], color[2]])
        return np.array(vertices, dtype=np.float32)

    def _update_animation(self):
        """Updates the animation angle and triggers a repaint."""
        self.moon_animation_angle += 0.03
        if self.moon_animation_angle > np.pi * 2:
            self.moon_animation_angle -= np.pi * 2
        self.update()

    def _generate_sphere_vertices(self, radius, sectors, stacks):
        """Generates vertices and indices for a sphere."""
        vertices, indices = [], []
        for i in range(stacks + 1):
            stack_angle = np.pi / 2 - i * np.pi / stacks
            xy = radius * np.cos(stack_angle)
            z = radius * np.sin(stack_angle)
            for j in range(sectors + 1):
                sector_angle = j * 2 * np.pi / sectors
                x = xy * np.cos(sector_angle)
                y = xy * np.sin(sector_angle)
                vertices.extend([x, y, z])
        for i in range(stacks):
            k1, k2 = i * (sectors + 1), (i + 1) * (sectors + 1)
            for j in range(sectors):
                if i != 0: indices.extend([k1 + j, k2 + j, k1 + j + 1])
                if i != (stacks - 1): indices.extend([k1 + j + 1, k2 + j, k2 + j + 1])
        return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

    def initializeGL(self):
        glClearColor(0.05, 0.07, 0.09, 1.0)
        glEnable(GL_DEPTH_TEST)
        glLineWidth(2.0)

        # --- Gradient Shader (for spiral) ---
        vertex_shader = """
        #version 330 core
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec3 a_color;
        uniform mat4 model; uniform mat4 view; uniform mat4 projection;
        out vec3 vertex_color;
        void main() {
            gl_Position = projection * view * model * vec4(a_position, 1.0);
            vertex_color = a_color;
        }"""
        fragment_shader_gradient = """
        #version 330 core
        in vec3 vertex_color; out vec4 FragColor;
        void main() { FragColor = vec4(vertex_color, 1.0); }"""
        self.gradient_shader = QOpenGLShaderProgram()
        self.gradient_shader.addShaderFromSourceCode(QOpenGLShaderProgram.ShaderTypeBit.Vertex, vertex_shader)
        self.gradient_shader.addShaderFromSourceCode(QOpenGLShaderProgram.ShaderTypeBit.Fragment, fragment_shader_gradient)
        self.gradient_shader.link()

        # --- Solid Color Shader (for planets/lamp) ---
        fragment_shader_solid = """
        #version 330 core
        uniform vec4 object_color; out vec4 FragColor;
        void main() { FragColor = object_color; }"""
        self.solid_shader = QOpenGLShaderProgram()
        self.solid_shader.addShaderFromSourceCode(QOpenGLShaderProgram.ShaderTypeBit.Vertex, vertex_shader)
        self.solid_shader.addShaderFromSourceCode(QOpenGLShaderProgram.ShaderTypeBit.Fragment, fragment_shader_solid)
        self.solid_shader.link()

        # --- Buffer for Spiral ---
        spiral_vertices = self._generate_spiral_vertices()
        self.spiral_vertex_count = len(spiral_vertices) // 6
        self.spiral_vao.create()
        self.spiral_vao.bind()
        self.spiral_vbo.create()
        self.spiral_vbo.bind()
        self.spiral_vbo.allocate(spiral_vertices.tobytes(), len(spiral_vertices) * 4)
        self.gradient_shader.enableAttributeArray(0)
        self.gradient_shader.setAttributeBuffer(0, GL_FLOAT, 0, 3, 6 * 4)
        self.gradient_shader.enableAttributeArray(1)
        self.gradient_shader.setAttributeBuffer(1, GL_FLOAT, 3 * 4, 3, 6 * 4)
        self.spiral_vao.release()

        # --- Buffer for Unit Sphere ---
        sphere_vertices, sphere_indices = self._generate_sphere_vertices(1.0, 20, 10)
        self.sphere_index_count = len(sphere_indices)
        self.sphere_vao.create()
        self.sphere_vao.bind()
        self.sphere_vbo.create()
        self.sphere_vbo.bind()
        self.sphere_vbo.allocate(sphere_vertices.tobytes(), len(sphere_vertices) * 4)
        self.sphere_ebo.create()
        self.sphere_ebo.bind()
        self.sphere_ebo.allocate(sphere_indices.tobytes(), len(sphere_indices) * 4)
        self.solid_shader.enableAttributeArray(0)
        self.solid_shader.setAttributeBuffer(0, GL_FLOAT, 0, 3, 0)
        self.sphere_vao.release()

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)
        aspect = w / h if h > 0 else 1
        self.projection_matrix.setToIdentity()
        self.projection_matrix.ortho(-500 * aspect, 500 * aspect, -500, 500, -1000, 1000)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.view_matrix.setToIdentity()
        self.view_matrix.lookAt(QVector3D(500, 400, 500), QVector3D(0, -100, 0), QVector3D(0, 1, 0))

        # --- Draw Spiral ---
        self.gradient_shader.bind()
        self.gradient_shader.setUniformValue("projection", self.projection_matrix)
        self.gradient_shader.setUniformValue("view", self.view_matrix)
        self.gradient_shader.setUniformValue("model", QMatrix4x4())
        self.spiral_vao.bind()
        glDrawArrays(GL_LINE_STRIP, 0, self.spiral_vertex_count)
        self.spiral_vao.release()
        self.gradient_shader.release()

        # --- Draw Planets and Lamp ---
        self.solid_shader.bind()
        self.solid_shader.setUniformValue("projection", self.projection_matrix)
        self.solid_shader.setUniformValue("view", self.view_matrix)
        self.sphere_vao.bind()

        # Draw Planets
        for course in self.courses:
            pos = self.spiral_path_points[int(course["progress"] * (len(self.spiral_path_points) - 1))]
            model_matrix = QMatrix4x4()
            model_matrix.translate(pos)
            model_matrix.scale(14) # Planet radius
            self.solid_shader.setUniformValue("model", model_matrix)
            self.solid_shader.setUniformValue("object_color", QVector3D(0.64, 0.61, 0.99)) # #a29bfe
            glDrawElements(GL_TRIANGLES, self.sphere_index_count, GL_UNSIGNED_INT, None)

            # --- Draw Moons ---
            moon_orbit_radius = 22
            moon_radius = 6

            # Moon 1 (Social, Green)
            moon1_angle = self.moon_animation_angle
            moon1_offset = QVector3D(moon_orbit_radius * np.cos(moon1_angle), moon_orbit_radius * np.sin(moon1_angle), 0)
            moon1_pos = pos + moon1_offset
            moon1_model_matrix = QMatrix4x4()
            moon1_model_matrix.translate(moon1_pos)
            moon1_model_matrix.scale(moon_radius)
            self.solid_shader.setUniformValue("model", moon1_model_matrix)
            self.solid_shader.setUniformValue("object_color", QVector3D(0.33, 0.94, 0.77)) # #55efc4
            glDrawElements(GL_TRIANGLES, self.sphere_index_count, GL_UNSIGNED_INT, None)

            # Moon 2 (Mentoring, Yellow)
            moon2_angle = self.moon_animation_angle + np.pi
            moon2_offset = QVector3D(moon_orbit_radius * np.cos(moon2_angle), moon_orbit_radius * np.sin(moon2_angle), 0)
            moon2_pos = pos + moon2_offset
            moon2_model_matrix = QMatrix4x4()
            moon2_model_matrix.translate(moon2_pos)
            moon2_model_matrix.scale(moon_radius)
            self.solid_shader.setUniformValue("model", moon2_model_matrix)
            self.solid_shader.setUniformValue("object_color", QVector3D(1.0, 0.92, 0.65)) # #ffeaa7
            glDrawElements(GL_TRIANGLES, self.sphere_index_count, GL_UNSIGNED_INT, None)

        # Draw Lamp
        # Bulb
        model_matrix = QMatrix4x4()
        model_matrix.translate(0, 0, 0)
        model_matrix.scale(25) # Bulb radius
        self.solid_shader.setUniformValue("model", model_matrix)
        self.solid_shader.setUniformValue("object_color", QVector3D(0.9, 0.9, 0.7)) # #FFFFE0
        glDrawElements(GL_TRIANGLES, self.sphere_index_count, GL_UNSIGNED_INT, None)
        # For simplicity, base and stand are omitted, lamp is just a central sphere for now

        self.sphere_vao.release()
        self.solid_shader.release()

class MainWindow(QMainWindow):
    """Main application window for the 3D visualization."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lamp: The Galactic Learning Path (3D)")
        self.setGeometry(100, 100, 1200, 900)

        self.gl_widget = GalacticGLWidget(self)
        self.setCentralWidget(self.gl_widget)

def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
