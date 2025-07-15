import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
import random
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GASimulatorApp:
    def __init__(self, master):
        self.master = master
        master.title("Genetic Algorithm Simulator")
        master.geometry("1000x700")

        # Main frame
        self.main_frame = ttk.Frame(master, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure resizing
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        # Visualization panel gets more weight
        self.main_frame.grid_columnconfigure(1, weight=3)

        # --- Left Panel ---
        self.left_panel = ttk.Frame(self.main_frame, padding="10")
        self.left_panel.grid(row=0, column=0, sticky="nswe")

        # --- Right Panel ---
        self.right_panel = ttk.Frame(self.main_frame, padding="10")
        self.right_panel.grid(row=0, column=1, sticky="nswe")

        self.create_widgets()

    def create_widgets(self):
        # --- Algorithm Settings ---
        settings_frame = ttk.LabelFrame(
            self.left_panel,
            text="Algorithm Settings",
            padding="10")
        settings_frame.pack(fill=tk.X, expand=True, pady=5)
        self.create_settings_widgets(settings_frame)

        # --- Control & Status ---
        control_frame = ttk.LabelFrame(
            self.left_panel,
            text="Control and Status",
            padding="10")
        control_frame.pack(fill=tk.X, expand=True, pady=5)
        self.create_control_widgets(control_frame)

        # --- Visualization ---
        vis_frame = ttk.LabelFrame(
            self.right_panel,
            text="Performance Visualization",
            padding="10")
        vis_frame.pack(fill=tk.BOTH, expand=True)
        self.create_visualization_widgets(vis_frame)

        self.ga_solver = GASolver(self)
        self.setup_problem_data()

    def setup_problem_data(self):
        self.TSP_CITIES = [
            (60, 200), (180, 200), (80, 180), (140, 180), (20, 160),
            (100, 160), (200, 160), (120, 140), (40, 120), (160, 120),
            (180, 100), (60, 80), (120, 80), (100, 60), (20, 40),
            (200, 40), (40, 20), (160, 20)
        ]
        self.KNAPSACK_ITEMS = [
            {"name": "Item A", "weight": 10, "value": 60},
            {"name": "Item B", "weight": 20, "value": 100},
            {"name": "Item C", "weight": 30, "value": 120},
            {"name": "Item D", "weight": 15, "value": 70},
            {"name": "Item E", "weight": 5, "value": 30},
            {"name": "Item F", "weight": 25, "value": 90},
            {"name": "Item G", "weight": 35, "value": 150},
        ]
        self.KNAPSACK_CAPACITY = 50

    def create_settings_widgets(self, parent_frame):
        # Population Size
        self.pop_size_var = tk.IntVar(value=50)
        ttk.Label(
            parent_frame,
            text="Population Size:").grid(
            row=0,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=10,
            to=200,
            variable=self.pop_size_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.pop_size_label.config(
                text=f"{int(float(v))}")).grid(
            row=0,
            column=1,
            sticky="we")
        self.pop_size_label = ttk.Label(parent_frame, text="50")
        self.pop_size_label.grid(row=0, column=2, padx=5)

        # Number of Generations
        self.generations_var = tk.IntVar(value=100)
        ttk.Label(
            parent_frame,
            text="Number of Generations:").grid(
            row=1,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=10,
            to=500,
            variable=self.generations_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.generations_label.config(
                text=f"{int(float(v))}")).grid(
            row=1,
            column=1,
            sticky="we")
        self.generations_label = ttk.Label(parent_frame, text="100")
        self.generations_label.grid(row=1, column=2, padx=5)

        # Crossover Rate
        self.crossover_rate_var = tk.DoubleVar(value=0.8)
        ttk.Label(
            parent_frame,
            text="Crossover Rate:").grid(
            row=2,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=0.0,
            to=1.0,
            variable=self.crossover_rate_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.crossover_rate_label.config(
                text=f"{float(v):.2f}")).grid(
            row=2,
            column=1,
            sticky="we")
        self.crossover_rate_label = ttk.Label(parent_frame, text="0.80")
        self.crossover_rate_label.grid(row=2, column=2, padx=5)

        # Mutation Rate
        self.mutation_rate_var = tk.DoubleVar(value=0.05)
        ttk.Label(
            parent_frame,
            text="Mutation Rate:").grid(
            row=3,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=0.0,
            to=0.5,
            variable=self.mutation_rate_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.mutation_rate_label.config(
                text=f"{float(v):.2f}")).grid(
            row=3,
            column=1,
            sticky="we")
        self.mutation_rate_label = ttk.Label(parent_frame, text="0.05")
        self.mutation_rate_label.grid(row=3, column=2, padx=5)

        # Mutation Strength
        self.mutation_strength_var = tk.DoubleVar(value=0.5)
        ttk.Label(
            parent_frame,
            text="Mutation Strength:").grid(
            row=4,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=0.01,
            to=2.0,
            variable=self.mutation_strength_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.mutation_strength_label.config(
                text=f"{float(v):.2f}")).grid(
            row=4,
            column=1,
            sticky="we")
        self.mutation_strength_label = ttk.Label(parent_frame, text="0.50")
        self.mutation_strength_label.grid(row=4, column=2, padx=5)

        # Elitism Count
        self.elitism_count_var = tk.IntVar(value=2)
        ttk.Label(
            parent_frame,
            text="Elitism Count:").grid(
            row=5,
            column=0,
            sticky="w",
            pady=2)
        ttk.Scale(
            parent_frame,
            from_=0,
            to=10,
            variable=self.elitism_count_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self.elitism_count_label.config(
                text=f"{int(float(v))}")).grid(
            row=5,
            column=1,
            sticky="we")
        self.elitism_count_label = ttk.Label(parent_frame, text="2")
        self.elitism_count_label.grid(row=5, column=2, padx=5)

        # Gene Range
        ttk.Label(parent_frame,
                  text="Gene Range (Min/Max):").grid(row=6,
                                                     column=0,
                                                     sticky="w",
                                                     pady=2)
        self.gene_min_var = tk.DoubleVar(value=-5.0)
        self.gene_max_var = tk.DoubleVar(value=5.0)
        ttk.Entry(
            parent_frame,
            textvariable=self.gene_min_var,
            width=10).grid(
            row=6,
            column=1,
            sticky="w",
            padx=5)
        ttk.Entry(
            parent_frame,
            textvariable=self.gene_max_var,
            width=10).grid(
            row=6,
            column=1,
            sticky="e",
            padx=5)

        # Problem Selection
        ttk.Label(
            parent_frame,
            text="Select Problem:").grid(
            row=7,
            column=0,
            sticky="w",
            pady=2)
        self.problem_var = tk.StringVar()
        self.problem_combo = ttk.Combobox(
            parent_frame,
            textvariable=self.problem_var,
            values=[
                "Sphere Function",
                "Rastrigin Function",
                "Traveling Salesperson Problem (TSP)",
                "Knapsack Problem"])
        self.problem_combo.grid(row=7, column=1, sticky="we", columnspan=2)
        self.problem_combo.current(0)

    def create_control_widgets(self, parent_frame):
        self.start_button = ttk.Button(
            parent_frame, text="Start GA", command=self.start_ga)
        self.start_button.pack(pady=5)

        self.stop_button = ttk.Button(
            parent_frame,
            text="Stop GA",
            command=self.stop_ga,
            state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        self.reset_button = ttk.Button(
            parent_frame, text="Reset", command=self.reset_ga)
        self.reset_button.pack(pady=5)

        self.export_button = ttk.Button(
            parent_frame,
            text="Export Data",
            command=self.export_data)
        self.export_button.pack(pady=5)

        self.status_label = ttk.Label(parent_frame, text="Status: Ready")
        self.status_label.pack(pady=5)

        self.generation_label = ttk.Label(parent_frame, text="Generation: N/A")
        self.generation_label.pack(pady=5)

        self.best_fitness_label = ttk.Label(
            parent_frame, text="Best Fitness: N/A")
        self.best_fitness_label.pack(pady=5)

        self.avg_fitness_label = ttk.Label(
            parent_frame, text="Avg Fitness: N/A")
        self.avg_fitness_label.pack(pady=5)

        self.best_solution_label = ttk.Label(
            parent_frame, text="Best Solution: N/A")
        self.best_solution_label.pack(pady=5)

    def create_visualization_widgets(self, parent_frame):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def start_ga(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running...")
        self.ga_thread = threading.Thread(
            target=self.ga_solver.run_genetic_algorithm_gui, daemon=True)
        try:
            self.ga_thread = threading.Thread(
                target=self.ga_solver.run_genetic_algorithm_gui, daemon=True)
            self.ga_thread.start()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to start GA thread: {e}")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Error")

    def stop_ga(self):
        """Signals the GA thread to stop gracefully."""
        self.ga_solver.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)

    def reset_ga(self):
        # Reset GUI elements to default values
        self.pop_size_var.set(50)
        self.generations_var.set(100)
        self.crossover_rate_var.set(0.8)
        self.mutation_rate_var.set(0.05)
        self.mutation_strength_var.set(0.5)
        self.elitism_count_var.set(2)
        self.gene_min_var.set(-5.0)
        self.gene_max_var.set(5.0)
        self.problem_combo.current(0)
        self.status_label.config(text="Status: Ready")
        self.generation_label.config(text="Generation: N/A")
        self.best_fitness_label.config(text="Best Fitness: N/A")
        self.avg_fitness_label.config(text="Avg Fitness: N/A")
        self.best_solution_label.config(text="Best Solution: N/A")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        # Clear plots if they exist
        if hasattr(self, 'ax'):
            self.ax.clear()
            self.canvas.draw()

    def export_data(self):
        if not hasattr(
                self.ga_solver,
                'best_fitness_history') or not self.ga_solver.best_fitness_history:
            tk.messagebox.showinfo(
                "Export Error",
                "No data to export. Please run the GA first.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[
                ("CSV files", "*.csv"), ("All files", "*.*")])
        if not filepath:
            return
        with open(filepath, 'w', newline='') as f:
            f.write("Generation,Best Fitness,Average Fitness\n")
            for i in range(len(self.ga_solver.best_fitness_history)):
                f.write(
                    f"{i + 1},{self.ga_solver.best_fitness_history[i]},{self.ga_solver.avg_fitness_history[i]}\n")
        tk.messagebox.showinfo(
            "Export Success",
            f"Data exported to {filepath}")


class GASolver:
    def __init__(self, app):
        self.app = app
        self.population = []
        self.fitnesses = []
        self.stop_event = threading.Event()

    def run_genetic_algorithm_gui(self):
        self.stop_event.clear()
        problem_type = self.app.problem_var.get()
        pop_size = self.app.pop_size_var.get()
        num_genes = self.get_num_genes(problem_type)
        gene_range = (self.app.gene_min_var.get(), self.app.gene_max_var.get())
        self.population = self.initialize_population(
            pop_size, num_genes, gene_range, problem_type)

        self.best_fitness_history = []
        self.avg_fitness_history = []

        for generation in range(self.app.generations_var.get()):
            if self.stop_event.is_set():
                break

            self.calculate_fitness(problem_type)
            best_fitness = np.max(self.fitnesses)
            avg_fitness = np.mean(self.fitnesses)
            self.best_fitness_history.append(best_fitness)
            self.avg_fitness_history.append(avg_fitness)
            best_solution = self.population[np.argmax(self.fitnesses)]

            self.app.master.after(
                0,
                self.update_gui,
                generation + 1,
                best_fitness,
                avg_fitness,
                best_solution,
                problem_type)

            next_population = self.create_next_generation(
                problem_type, gene_range)
            self.population = next_population

        self.app.master.after(0, self.finalize_run)

    def update_gui(self, generation, best_fitness, avg_fitness, best_solution, problem_type):
        self.app.generation_label.config(
            text=f"Generation: {generation} / {self.app.generations_var.get()}")
        self.app.best_fitness_label.config(
            text=f"Best Fitness: {best_fitness:.4f}")
        self.app.avg_fitness_label.config(
            text=f"Avg Fitness: {avg_fitness:.4f}")
        solution_str = np.array2string(np.array(best_solution), formatter={
                                       'float_kind': lambda x: "%.4f" % x})
        self.app.best_solution_label.config(
            text=f"Best Solution: {solution_str}")
        self.update_plot(generation, best_solution, problem_type)

    def update_plot(self, generation, best_solution=None, problem_type=None):
        self.app.ax.clear()
        if problem_type == "Traveling Salesperson Problem (TSP)" and best_solution is not None:
            self.plot_tsp_tour(best_solution)
        elif problem_type == "Knapsack Problem" and best_solution is not None:
            self.plot_knapsack_solution(best_solution)
        else:
            self.app.ax.plot(self.best_fitness_history, label="Best Fitness")
            self.app.ax.plot(self.avg_fitness_history, label="Average Fitness")
            self.app.ax.set_xlabel("Generation")
            self.app.ax.set_ylabel("Fitness")
            self.app.ax.legend()
            self.app.ax.grid(True)
        self.app.canvas.draw()

    def plot_tsp_tour(self, tour):
        self.app.ax.clear()
        cities = self.app.TSP_CITIES
        self.app.ax.scatter([c[0] for c in cities], [c[1] for c in cities], c='red')
        for i in range(len(tour)):
            start_city_coords = cities[tour[i]]
            end_city_coords = cities[tour[(i + 1) % len(tour)]]
            self.app.ax.plot([start_city_coords[0], end_city_coords[0]],
                             [start_city_coords[1], end_city_coords[1]], 'b-')
        self.app.ax.set_title("Best TSP Tour")
        self.app.ax.set_xlabel("X Coordinate")
        self.app.ax.set_ylabel("Y Coordinate")

    def plot_knapsack_solution(self, solution):
        self.app.ax.clear()
        items = self.app.KNAPSACK_ITEMS
        selected_items = [items[i]['name'] for i, gene in enumerate(solution) if gene == 1]
        total_value = sum(items[i]['value'] for i, gene in enumerate(solution) if gene == 1)
        total_weight = sum(items[i]['weight'] for i, gene in enumerate(solution) if gene == 1)

        y_pos = np.arange(len(selected_items))
        self.app.ax.barh(y_pos, [items[i]['value'] for i, gene in enumerate(solution) if gene == 1], align='center')
        self.app.ax.set_yticks(y_pos)
        self.app.ax.set_yticklabels(selected_items)
        self.app.ax.invert_yaxis()  # labels read top-to-bottom
        self.app.ax.set_xlabel('Value')
        self.app.ax.set_title(f'Knapsack Solution: Value={total_value}, Weight={total_weight}')

    def finalize_run(self):
        self.app.status_label.config(text="Status: Completed")
        self.app.start_button.config(state=tk.NORMAL)
        self.app.stop_button.config(state=tk.DISABLED)

    def get_num_genes(self, problem_type):
        if problem_type == "Traveling Salesperson Problem (TSP)":
            return len(self.app.TSP_CITIES)
        elif problem_type == "Knapsack Problem":
            return len(self.app.KNAPSACK_ITEMS)
        return 2  # For Sphere and Rastrigin

    def calculate_fitness(self, problem_type):
        self.fitnesses = []
        for chromosome in self.population:
            if problem_type == "Sphere Function":
                self.fitnesses.append(self.sphere_function(chromosome))
            elif problem_type == "Rastrigin Function":
                self.fitnesses.append(self.rastrigin_function(chromosome))
            elif problem_type == "Traveling Salesperson Problem (TSP)":
                self.fitnesses.append(
                    self.tsp_fitness(
                        chromosome,
                        self.app.TSP_CITIES))
            elif problem_type == "Knapsack Problem":
                self.fitnesses.append(
                    self.knapsack_fitness(
                        chromosome,
                        self.app.KNAPSACK_ITEMS,
                        self.app.KNAPSACK_CAPACITY))

    def create_next_generation(self, problem_type, gene_range):
        next_population = []
        elitism_count = self.app.elitism_count_var.get()
        if elitism_count > 0:
            elite_indices = np.argsort(self.fitnesses)[-elitism_count:]
            for i in elite_indices:
                next_population.append(self.population[i])

        while len(next_population) < len(self.population):
            parent1 = self.roulette_wheel_selection(
                self.population, self.fitnesses)
            parent2 = self.roulette_wheel_selection(
                self.population, self.fitnesses)

            crossover_rate = self.app.crossover_rate_var.get()
            if problem_type in ["Sphere Function", "Rastrigin Function"]:
                child1, child2 = self.single_point_crossover(
                    parent1, parent2, crossover_rate)
            elif problem_type == "Traveling Salesperson Problem (TSP)":
                child1, child2 = self.order_crossover_ox(
                    parent1, parent2, crossover_rate)
            else:  # Knapsack
                child1, child2 = self.single_point_crossover(
                    parent1, parent2, crossover_rate)

            mutation_rate = self.app.mutation_rate_var.get()
            mutation_strength = self.app.mutation_strength_var.get()
            if problem_type in ["Sphere Function", "Rastrigin Function"]:
                child1 = self.gaussian_mutation(
                    child1, mutation_rate, mutation_strength, gene_range)
                child2 = self.gaussian_mutation(
                    child2, mutation_rate, mutation_strength, gene_range)
            elif problem_type == "Traveling Salesperson Problem (TSP)":
                child1 = self.swap_mutation(child1, mutation_rate)
                child2 = self.swap_mutation(child2, mutation_rate)
            else:  # Knapsack
                child1 = self.bit_flip_mutation(child1, mutation_rate)
                child2 = self.bit_flip_mutation(child2, mutation_rate)

            next_population.append(child1)
            if len(next_population) < len(self.population):
                next_population.append(child2)
        return next_population

    # --- Fitness Functions ---
    def sphere_function(self, chromosome):
        return 1 / (1 + np.sum(np.square(chromosome)))

    def rastrigin_function(self, chromosome):
        return 1 / (1 + (10 * len(chromosome) +
                    np.sum(np.square(chromosome) - 10 * np.cos(2 * np.pi * chromosome))))

    def tsp_fitness(self, chromosome, city_coords):
        distance = 0
        for i in range(len(chromosome)):
            start_city = chromosome[i]
            end_city = chromosome[(i + 1) % len(chromosome)]
            distance += np.linalg.norm(
                np.array(
                    city_coords[start_city]) -
                np.array(
                    city_coords[end_city]))
        return 1 / (1 + distance)

    def knapsack_fitness(self, chromosome, items, capacity):
        total_value = 0
        total_weight = 0
        for i, gene in enumerate(chromosome):
            if gene == 1:
                total_value += items[i]['value']
                total_weight += items[i]['weight']
        if total_weight > capacity:
            return 0  # Penalize for overweight
        return total_value

    # --- GA Operators ---
    def initialize_population(
            self,
            pop_size,
            num_genes,
            gene_range,
            problem_type):
        self.population = []
        if problem_type in ["Sphere Function", "Rastrigin Function"]:
            for _ in range(pop_size):
                self.population.append(
                    np.random.uniform(
                        gene_range[0],
                        gene_range[1],
                        num_genes))
        elif problem_type == "Traveling Salesperson Problem (TSP)":
            for _ in range(pop_size):
                self.population.append(
                    np.random.permutation(num_genes).tolist())
        elif problem_type == "Knapsack Problem":
            for _ in range(pop_size):
                self.population.append(
                    np.random.randint(
                        0, 2, num_genes).tolist())
        return self.population

    def roulette_wheel_selection(self, population, fitnesses):
        total_fitness = sum(fitnesses)
        if total_fitness == 0:
            return random.choice(population)
        selection_probs = [f / total_fitness for f in fitnesses]
        return population[np.random.choice(len(population), p=selection_probs)]

    def single_point_crossover(self, parent1, parent2, crossover_rate):
        if random.random() < crossover_rate:
            point = random.randint(1, len(parent1) - 1)
            child1 = np.concatenate((parent1[:point], parent2[point:]))
            child2 = np.concatenate((parent2[:point], parent1[point:]))
            return child1, child2
        return parent1, parent2

    def order_crossover_ox(self, parent1, parent2, crossover_rate):
        if random.random() < crossover_rate:
            size = len(parent1)
            child1, child2 = [-1] * size, [-1] * size
            start, end = sorted(random.sample(range(size), 2))
            child1[start:end] = parent1[start:end]
            child2[start:end] = parent2[start:end]
            p1_genes = [gene for gene in parent2 if gene not in child1]
            p2_genes = [gene for gene in parent1 if gene not in child2]
            for i in range(size):
                if child1[i] == -1:
                    child1[i] = p1_genes.pop(0)
                if child2[i] == -1:
                    child2[i] = p2_genes.pop(0)
            return child1, child2
        return parent1, parent2

    def bit_flip_mutation(self, chromosome, mutation_rate):
        for i in range(len(chromosome)):
            if random.random() < mutation_rate:
                chromosome[i] = 1 - chromosome[i]
        return chromosome

    def gaussian_mutation(
            self,
            chromosome,
            mutation_rate,
            mutation_strength,
            gene_range):
        for i in range(len(chromosome)):
            if random.random() < mutation_rate:
                chromosome[i] += np.random.normal(0, mutation_strength)
                chromosome[i] = np.clip(
                    chromosome[i], gene_range[0], gene_range[1])
        return chromosome

    def swap_mutation(self, chromosome, mutation_rate):
        if random.random() < mutation_rate:
            idx1, idx2 = random.sample(range(len(chromosome)), 2)
            chromosome[idx1], chromosome[idx2] = chromosome[idx2], chromosome[idx1]
        return chromosome


if __name__ == "__main__":
    root = tk.Tk()
    app = GASimulatorApp(root)
    root.mainloop()
