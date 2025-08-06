import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget,
                             QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
                             QTableView, QMessageBox, QHeaderView)
from PyQt5.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel
from PyQt5.QtGui import QFont

# --- Backend Imports ---
from data_processor import load_and_validate

# --- Pandas Model for QTableView ---
class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None

# --- Page Classes ---

class DataLoadingPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.df = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("مرحله ۱: بارگذاری مجموعه داده")
        title_label.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)

        # File Selection Button
        self.select_file_button = QPushButton("انتخاب فایل CSV")
        self.select_file_button.clicked.connect(self.open_file_dialog)

        # Filename Label
        self.filename_label = QLabel("فایلی انتخاب نشده است.")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setStyleSheet("color: #AAA;")

        # Table View for Data Preview
        self.table_view = QTableView()
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Continue Button
        self.continue_button = QPushButton("ادامه و پیش‌پردازش")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.proceed)

        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(self.select_file_button)
        layout.addWidget(self.filename_label)
        layout.addWidget(self.table_view)
        layout.addWidget(self.continue_button)

        self.setLayout(layout)

    def open_file_dialog(self):
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if filepath:
            try:
                self.df = load_and_validate(filepath)
                self.filename_label.setText(f"فایل بارگذاری شده: {filepath}")

                # Store the full dataframe in the main_window
                self.main_window.dataframe = self.df

                # Create a model for the table view (first 50 rows)
                preview_df = self.df.head(50)
                model = PandasModel(preview_df)
                self.table_view.setModel(model)

                self.continue_button.setEnabled(True)

            except Exception as e:
                QMessageBox.critical(self, "خطا در بارگذاری فایل", str(e))
                self.filename_label.setText("خطا در بارگذاری فایل.")
                self.main_window.dataframe = None
                self.table_view.setModel(None)
                self.continue_button.setEnabled(False)

    def proceed(self):
        # This function will be called when the continue button is clicked
        # It will eventually pass the dataframe to the next page
        self.main_window.go_to_config_page()


import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget,
                             QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
                             QTableView, QMessageBox, QHeaderView, QGroupBox, QFormLayout,
                             QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, QProgressDialog)
from PyQt5.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# --- Backend Imports ---
from data_processor import load_and_validate, preprocess
from model_trainer import train_and_predict

# --- Matplotlib Canvas Widget ---
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#1E1E1E')
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#1E1E1E')
        self.axes.tick_params(axis='x', colors='#F0F0F0')
        self.axes.tick_params(axis='y', colors='#F0F0F0')
        self.axes.spines['bottom'].set_color('#F0F0F0')
        self.axes.spines['top'].set_color('#F0F0F0')
        self.axes.spines['right'].set_color('#F0F0F0')
        self.axes.spines['left'].set_color('#F0F0F0')
        self.axes.xaxis.label.set_color('#F0F0F0')
        self.axes.yaxis.label.set_color('#F0F0F0')
        self.axes.title.set_color('#F0F0F0')
        super(MplCanvas, self).__init__(self.fig)

# --- Pandas Model for QTableView ---
class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None

# --- Worker for Threading ---
class Worker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, df, model_name, params, forecast_horizon, value_col):
        super().__init__()
        self.df = df
        self.model_name = model_name
        self.params = params
        self.forecast_horizon = forecast_horizon
        self.value_col = value_col

    def run(self):
        try:
            results = train_and_predict(self.df, self.model_name, self.params, self.forecast_horizon, self.value_col)
            self.finished.emit(results)
        except Exception as e:
            import traceback
            self.error.emit(f"Error in model training: {e}\n{traceback.format_exc()}")

# --- Page Classes ---

class DataLoadingPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.df = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = QLabel("مرحله ۱: بارگذاری مجموعه داده")
        title_label.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)

        self.select_file_button = QPushButton("انتخاب فایل CSV")
        self.select_file_button.clicked.connect(self.open_file_dialog)

        self.filename_label = QLabel("فایلی انتخاب نشده است.")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setStyleSheet("color: #AAA;")

        self.table_view = QTableView()
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.continue_button = QPushButton("ادامه و پیش‌پردازش")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.proceed)

        layout.addWidget(title_label)
        layout.addWidget(self.select_file_button)
        layout.addWidget(self.filename_label)
        layout.addWidget(self.table_view)
        layout.addWidget(self.continue_button)

        self.setLayout(layout)

    def open_file_dialog(self):
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if filepath:
            try:
                self.df = load_and_validate(filepath)
                self.filename_label.setText(f"فایل بارگذاری شده: {filepath}")

                self.main_window.dataframe = self.df
                self.main_window.preprocessed_dataframe = None # Reset preprocessed data

                preview_df = self.df.head(50)
                model = PandasModel(preview_df)
                self.table_view.setModel(model)

                self.continue_button.setEnabled(True)

            except Exception as e:
                QMessageBox.critical(self, "خطا در بارگذاری فایل", str(e))
                self.filename_label.setText("خطا در بارگذاری فایل.")
                self.main_window.dataframe = None
                self.table_view.setModel(None)
                self.continue_button.setEnabled(False)

    def proceed(self):
        self.main_window.go_to_config_page()


class ConfigPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        back_button_layout = QHBoxLayout()
        self.back_button = QPushButton("بازگشت به بارگذاری داده")
        self.back_button.clicked.connect(self.main_window.go_to_data_loading_page)
        self.back_button.setFixedWidth(200)
        back_button_layout.addWidget(self.back_button)
        back_button_layout.addStretch()
        main_layout.addLayout(back_button_layout)

        self.preprocess_group = self._create_preprocessing_group()
        main_layout.addWidget(self.preprocess_group)

        self.model_selection_group = self._create_model_selection_group()
        main_layout.addWidget(self.model_selection_group)

        self.forecast_group = self._create_forecast_settings_group()
        main_layout.addWidget(self.forecast_group)

        main_layout.addStretch()

    def _create_preprocessing_group(self):
        group_box = QGroupBox("مرحله ۲: آماده‌سازی داده")
        group_box.setFont(QFont('Segoe UI', 14, QFont.Bold))
        layout = QFormLayout(group_box)

        self.timestamp_combo = QComboBox()
        self.value_combo = QComboBox()

        self.preprocess_button = QPushButton("اجرای پیش‌پردازش")
        self.preprocess_button.clicked.connect(self.run_preprocessing)
        self.preprocess_status_label = QLabel("هنوز اجرا نشده است.")
        self.preprocess_status_label.setStyleSheet("color: #AAA;")

        layout.addRow(QLabel("ستون زمان (Timestamp):"), self.timestamp_combo)
        layout.addRow(QLabel("ستون مقدار (Value):"), self.value_combo)
        layout.addRow(self.preprocess_button)
        layout.addRow(QLabel("وضعیت:"), self.preprocess_status_label)

        return group_box

    def run_preprocessing(self):
        timestamp_col = self.timestamp_combo.currentText()
        value_col = self.value_combo.currentText()

        if not timestamp_col or not value_col:
            QMessageBox.warning(self, "خطا", "لطفاً ستون زمان و مقدار را انتخاب کنید.")
            return
        if timestamp_col == value_col:
            QMessageBox.warning(self, "خطا", "ستون زمان و مقدار نمی‌توانند یکسان باشند.")
            return

        try:
            processed_df, report = preprocess(self.main_window.dataframe, timestamp_col, value_col)
            self.main_window.preprocessed_dataframe = processed_df
            self.main_window.value_col = value_col # Store value col name
            self.preprocess_status_label.setText(report)
            self.preprocess_status_label.setStyleSheet("color: #00AEEF;")
            self.train_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "خطا در پیش‌پردازش", str(e))
            self.preprocess_status_label.setText("پیش‌پردازش ناموفق بود.")
            self.preprocess_status_label.setStyleSheet("color: red;")
            self.train_button.setEnabled(False)

    def _create_model_selection_group(self):
        group_box = QGroupBox("مرحله ۳: انتخاب مدل و تنظیمات")
        group_box.setFont(QFont('Segoe UI', 14, QFont.Bold))
        layout = QVBoxLayout(group_box)

        form_layout = QFormLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["XGBoost", "Prophet", "ARIMA"])
        form_layout.addRow(QLabel("مدل را انتخاب کنید:"), self.model_combo)

        layout.addLayout(form_layout)

        self.hyperparam_stack = QStackedWidget()
        self.hyperparam_stack.addWidget(self._create_xgboost_params())
        self.hyperparam_stack.addWidget(self._create_prophet_params())
        self.hyperparam_stack.addWidget(self._create_arima_params())

        layout.addWidget(self.hyperparam_stack)

        self.model_combo.currentIndexChanged.connect(self.hyperparam_stack.setCurrentIndex)

        return group_box

    def _create_param_widget(self, name, tooltip, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        label = QLabel(name)

        icon = QLabel(" (?)")
        icon.setToolTip(tooltip)
        icon.setStyleSheet("color: #00AEEF; font-weight: bold;")

        layout.addWidget(label)
        layout.addWidget(icon)
        layout.addStretch()
        layout.addWidget(widget)
        return container

    def _create_xgboost_params(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.xgb_estimators = QSpinBox()
        self.xgb_estimators.setRange(50, 500)
        self.xgb_estimators.setValue(100)
        self.xgb_max_depth = QSpinBox()
        self.xgb_max_depth.setRange(3, 15)
        self.xgb_max_depth.setValue(5)
        self.xgb_learning_rate = QDoubleSpinBox()
        self.xgb_learning_rate.setRange(0.01, 0.3)
        self.xgb_learning_rate.setSingleStep(0.01)
        self.xgb_learning_rate.setValue(0.1)

        layout.addRow(self._create_param_widget("n_estimators:", "تعداد درختان تصمیم در مدل.", self.xgb_estimators))
        layout.addRow(self._create_param_widget("max_depth:", "حداکثر عمق هر درخت.", self.xgb_max_depth))
        layout.addRow(self._create_param_widget("learning_rate:", "نرخ یادگیری.", self.xgb_learning_rate))
        return widget

    def _create_prophet_params(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.prophet_changepoint = QDoubleSpinBox()
        self.prophet_changepoint.setRange(0.01, 0.5)
        self.prophet_changepoint.setSingleStep(0.01)
        self.prophet_changepoint.setValue(0.05)
        self.prophet_seasonality = QComboBox()
        self.prophet_seasonality.addItems(["additive", "multiplicative"])

        layout.addRow(self._create_param_widget("changepoint_prior_scale:", "میزان انعطاف‌پذیری مدل در نقاط تغییر روند.", self.prophet_changepoint))
        layout.addRow(self._create_param_widget("seasonality_mode:", "نوع فصلی بودن (افزایشی یا ضربی).", self.prophet_seasonality))
        return widget

    def _create_arima_params(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.arima_p = QSpinBox()
        self.arima_p.setRange(1, 10)
        self.arima_p.setValue(5)
        self.arima_d = QSpinBox()
        self.arima_d.setRange(0, 3)
        self.arima_d.setValue(1)
        self.arima_q = QSpinBox()
        self.arima_q.setRange(1, 10)
        self.arima_q.setValue(0)

        layout.addRow(self._create_param_widget("p (Order of AR):", "مرتبه بخش خودهمبستگی.", self.arima_p))
        layout.addRow(self._create_param_widget("d (Degree of differencing):", "مرتبه تفاضل‌گیری.", self.arima_d))
        layout.addRow(self._create_param_widget("q (Order of MA):", "مرتبه بخش میانگین متحرک.", self.arima_q))
        return widget

    def _create_forecast_settings_group(self):
        group_box = QGroupBox("مرحله ۴: تنظیمات خروجی")
        group_box.setFont(QFont('Segoe UI', 14, QFont.Bold))
        layout = QVBoxLayout(group_box)

        self.horizon_24 = QRadioButton("۲۴ ساعت آینده")
        self.horizon_48 = QRadioButton("۴۸ ساعت آینده")
        self.horizon_24.setChecked(True)

        horizon_layout = QHBoxLayout()
        horizon_layout.addWidget(self.horizon_24)
        horizon_layout.addWidget(self.horizon_48)
        horizon_layout.addStretch()

        self.train_button = QPushButton("شروع آموزش و پیش‌بینی")
        self.train_button.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.train_button.setStyleSheet("padding: 15px;")
        self.train_button.setEnabled(False) # Disabled until preprocessing is done
        self.train_button.clicked.connect(self.main_window.start_training_process)

        layout.addLayout(horizon_layout)
        layout.addWidget(self.train_button)
        return group_box

    def get_all_parameters(self):
        params = {}
        params['model_name'] = self.model_combo.currentText()

        model_name = params['model_name']
        if model_name == 'XGBoost':
            params['hyperparameters'] = {
                'n_estimators': self.xgb_estimators.value(),
                'max_depth': self.xgb_max_depth.value(),
                'learning_rate': self.xgb_learning_rate.value()
            }
        elif model_name == 'Prophet':
            params['hyperparameters'] = {
                'changepoint_prior_scale': self.prophet_changepoint.value(),
                'seasonality_mode': self.prophet_seasonality.currentText()
            }
        elif model_name == 'ARIMA':
            params['hyperparameters'] = {
                'p': self.arima_p.value(),
                'd': self.arima_d.value(),
                'q': self.arima_q.value()
            }

        params['forecast_horizon'] = 24 if self.horizon_24.isChecked() else 48

        return params

    def on_enter(self):
        """Called when this page becomes active."""
        if self.main_window.dataframe is not None:
            columns = self.main_window.dataframe.columns.tolist()

            current_ts = self.timestamp_combo.currentText()
            current_val = self.value_combo.currentText()

            self.timestamp_combo.clear()
            self.value_combo.clear()
            self.timestamp_combo.addItems(columns)
            self.value_combo.addItems(columns)

            if current_ts in columns:
                self.timestamp_combo.setCurrentText(current_ts)
            if current_val in columns:
                self.value_combo.setCurrentText(current_val)

            # Reset status if new data is loaded
            if self.main_window.preprocessed_dataframe is None:
                self.preprocess_status_label.setText("هنوز اجرا نشده است.")
                self.preprocess_status_label.setStyleSheet("color: #AAA;")
                self.train_button.setEnabled(False)


class ResultsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.results = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel("نتایج پیش‌بینی")
        title_label.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)

        # Main Plot
        self.main_plot_canvas = MplCanvas(self, width=10, height=5, dpi=100)

        # Metrics
        metrics_group = QGroupBox("معیارهای ارزیابی")
        metrics_group.setFont(QFont('Segoe UI', 14, QFont.Bold))
        metrics_layout = QHBoxLayout(metrics_group)
        self.mape_label = QLabel("MAPE: -")
        self.mape_label.setFont(QFont('Segoe UI', 16))
        self.rmse_label = QLabel("RMSE: -")
        self.rmse_label.setFont(QFont('Segoe UI', 16))
        metrics_layout.addStretch()
        metrics_layout.addWidget(self.mape_label)
        metrics_layout.addStretch()
        metrics_layout.addWidget(self.rmse_label)
        metrics_layout.addStretch()

        # Future Plot
        self.future_plot_canvas = MplCanvas(self, width=10, height=3, dpi=100)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("ذخیره پیش‌بینی (CSV)")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_forecast)
        self.home_button = QPushButton("بازگشت به شروع")
        self.home_button.clicked.connect(self.main_window.go_to_data_loading_page)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.home_button)
        buttons_layout.addStretch()

        layout.addWidget(title_label)
        layout.addWidget(self.main_plot_canvas, 7) # 70% stretch
        layout.addWidget(metrics_group, 1) # 10% stretch
        layout.addWidget(self.future_plot_canvas, 2) # 20% stretch
        layout.addLayout(buttons_layout)

    def update_results(self, results):
        self.results = results
        self.save_button.setEnabled(True)

        self.mape_label.setText(f"MAPE: {self.results['mape']:.2f} %")
        self.rmse_label.setText(f"RMSE: {self.results['rmse']:.2f}")

        # Update main plot
        self.main_plot_canvas.axes.clear()
        self.main_plot_canvas.axes.plot(self.results['historical_data'].index, self.results['historical_data'], color='gray', alpha=0.8, label='داده‌های تاریخی')
        self.main_plot_canvas.axes.plot(self.results['test_predictions'].index, self.results['test_predictions'], color='#00AEEF', linewidth=2, label='پیش‌بینی روی داده تست')
        self.main_plot_canvas.axes.legend(labelcolor='#F0F0F0')
        self.main_plot_canvas.axes.set_title("مقایسه داده‌های تاریخی و پیش‌بینی تست", color='#F0F0F0')
        self.main_plot_canvas.fig.tight_layout()
        self.main_plot_canvas.draw()

        # Update future plot
        self.future_plot_canvas.axes.clear()
        self.future_plot_canvas.axes.plot(self.results['future_forecast'].index, self.results['future_forecast'], color='#50C878', linestyle='--', marker='o', label='پیش‌بینی آینده')
        self.future_plot_canvas.axes.legend(labelcolor='#F0F0F0')
        self.future_plot_canvas.axes.set_title("پیش‌بینی آینده", color='#F0F0F0')
        self.future_plot_canvas.fig.tight_layout()
        self.future_plot_canvas.draw()

    def save_forecast(self):
        if self.results and self.results['future_forecast'] is not None:
            options = QFileDialog.Options()
            filepath, _ = QFileDialog.getSaveFileName(self, "ذخیره پیش‌بینی", "", "CSV Files (*.csv);;All Files (*)", options=options)
            if filepath:
                try:
                    self.results['future_forecast'].to_csv(filepath)
                    QMessageBox.information(self, "موفقیت", f"پیش‌بینی با موفقیت در فایل زیر ذخیره شد:\n{filepath}")
                except Exception as e:
                    QMessageBox.critical(self, "خطا در ذخیره‌سازی", str(e))

# --- Main Window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Time Series Forecasting Studio")
        self.setGeometry(100, 100, 1200, 800)
        self.dataframe = None
        self.preprocessed_dataframe = None
        self.value_col = None
        self.thread = None
        self.worker = None

        self.data_loading_page = DataLoadingPage(self)
        self.config_page = ConfigPage(self)
        self.results_page = ResultsPage(self)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.data_loading_page)
        self.stacked_widget.addWidget(self.config_page)
        self.stacked_widget.addWidget(self.results_page)
        self.setCentralWidget(self.stacked_widget)

        self.stacked_widget.currentChanged.connect(self.on_page_changed)

        self.go_to_data_loading_page()

    def load_stylesheet(self):
        try:
            with open("style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Warning: style.qss not found. Using default styles.")

    def start_training_process(self):
        if self.preprocessed_dataframe is None:
            QMessageBox.warning(self, "خطا", "لطفا ابتدا داده‌ها را پیش‌پردازش کنید.")
            return

        config_params = self.config_page.get_all_parameters()

        self.progress_dialog = QProgressDialog("در حال آموزش مدل و پیش‌بینی...", "لغو", 0, 0, self)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = Worker(
            df=self.preprocessed_dataframe,
            model_name=config_params['model_name'],
            params=config_params['hyperparameters'],
            forecast_horizon=config_params['forecast_horizon'],
            value_col=self.value_col
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_training_success)
        self.worker.error.connect(self.on_training_error)
        self.thread.start()

    def on_training_success(self, results):
        self.progress_dialog.close()
        self.results_page.update_results(results)
        self.go_to_results_page()
        self.thread.quit()
        self.thread.wait()

    def on_training_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, "خطا در آموزش", error_message)
        self.thread.quit()
        self.thread.wait()

    def go_to_data_loading_page(self):
        self.stacked_widget.setCurrentWidget(self.data_loading_page)

    def go_to_config_page(self):
        if self.dataframe is not None:
            self.stacked_widget.setCurrentWidget(self.config_page)
        else:
            QMessageBox.warning(self, "No Data", "Please load a dataset before proceeding.")

    def go_to_results_page(self):
        self.stacked_widget.setCurrentWidget(self.results_page)

    def on_page_changed(self, index):
        current_widget = self.stacked_widget.widget(index)
        if hasattr(current_widget, 'on_enter'):
            current_widget.on_enter()

# --- Application Entry Point ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_stylesheet()
    window.show()
    sys.exit(app.exec_())
