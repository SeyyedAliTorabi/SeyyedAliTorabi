import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import sqlite3
import os
import threading
import bcrypt
import pandas as pd
import numpy as np
from persiantools.jdatetime import JalaliDate
from datetime import datetime
import pickle
import json

# AI/ML and Plotting Libraries
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, GRU, Conv1D, MaxPooling1D, Flatten
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Persian Text Handling
import arabic_reshaper
from bidi.algorithm import get_display as get_bidi_display

# --- 1. GENERAL ARCHITECTURE & CONFIGURATION ---

# Set CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Model Configuration
MODEL_CONFIG = {
  "XGBoost": {"ext": ".json"},
  "RNN": {"ext": ".h5"},
  "GRU": {"ext": ".h5"},
  "CNN1D": {"ext": ".h5"}
}

# Base directories
BASE_DIRS = ["./user_data", "./results", "./models"]
DB_PATH = "./app_local.db"

# --- 2. EMBEDDED IRANIAN CALENDAR (1390-1410) ---
calendar_local = json.loads("""
[{"date":"1390/01/01","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Nowruz"},{"date":"1390/01/02","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Nowruz"},{"date":"1390/01/03","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Nowruz"},{"date":"1390/01/04","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Nowruz"},{"date":"1390/01/05","is_national_holiday":0,"is_religious_holiday":0,"is_friday":1,"description":"Weekend"},{"date":"1390/01/06","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/07","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/08","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/09","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/10","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/11","is_national_holiday":0,"is_religious_holiday":0,"is_friday":0,"description":false},{"date":"1390/01/12","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Islamic Republic Day"},{"date":"1390/01/13","is_national_holiday":1,"is_religious_holiday":0,"is_friday":0,"description":"Sizdah Be-dar"},{"date":"1410/12/29","is_national_holiday":1,"is_religious_holiday":0,"is_friday":1,"description":"Nationalization of the Iranian oil industry"}]
""")

# Create a DataFrame for faster lookups
calendar_df = pd.DataFrame(calendar_local)
def jalali_to_gregorian_dt(jalali_str):
    """Converts a 'YYYY/MM/DD' Jalali string to a Gregorian date object."""
    try:
        y, m, d = map(int, jalali_str.split('/'))
        return JalaliDate(y, m, d).to_gregorian()
    except (ValueError, TypeError):
        return pd.NaT
calendar_df['date'] = calendar_df['date'].apply(jalali_to_gregorian_dt)
calendar_df['date'] = pd.to_datetime(calendar_df['date'])


# --- UTILITY FUNCTIONS ---
def get_display(text):
    """Reshapes and reorders text for correct display in Tkinter."""
    return get_bidi_display(arabic_reshaper.reshape(str(text)))

def show_persian_message(title, message, msg_type="info"):
    """Shows a messagebox with Persian text."""
    title_p = get_display(title)
    message_p = get_display(message)
    if msg_type == "info":
        messagebox.showinfo(title_p, message_p)
    elif msg_type == "warning":
        messagebox.showwarning(title_p, message_p)
    elif msg_type == "error":
        messagebox.showerror(title_p, message_p)

def ask_persian_question(title, question):
    """Shows a yes/no question box with Persian text."""
    return messagebox.askyesno(get_display(title), get_display(question))

class ToplevelDialog(ctk.CTkToplevel):
    """Custom dialog for more complex interactions."""
    def __init__(self, title, question, options):
        super().__init__()
        self.title(get_display(title))
        self.geometry("400x150")
        self.transient(self.master)
        self.grab_set()
        self.result = None

        self.label = ctk.CTkLabel(self, text=get_display(question), font=("Vazirmatn", 14))
        self.label.pack(pady=20, padx=20, expand=True, fill="both")

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(pady=10)

        for option_text in options:
            btn = ctk.CTkButton(self.button_frame, text=get_display(option_text), font=("Vazirmatn", 12),
                                command=lambda opt=option_text: self.set_result(opt))
            btn.pack(side="right", padx=10)

    def set_result(self, result):
        self.result = result
        self.destroy()

    def get(self):
        self.master.wait_window(self)
        return self.result

# --- 2. AUTHENTICATION & DATABASE ---
class DBManager:
    """Handles all SQLite database operations."""
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def setup_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                national_id TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_results (
                id INTEGER PRIMARY KEY,
                national_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                mae REAL, mape REAL, rmse REAL, mse REAL,
                timestamp TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def register_user(self, national_id, username, password):
        if not (national_id.isdigit() and len(national_id) == 10):
            return "کد ملی باید ۱۰ رقم و عددی باشد.", False

        self.cursor.execute("SELECT * FROM users WHERE national_id = ? OR username = ?", (national_id, username))
        if self.cursor.fetchone():
            return "کد ملی یا نام کاربری قبلا ثبت شده است.", False

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.cursor.execute("INSERT INTO users (national_id, username, password_hash) VALUES (?, ?, ?)",
                            (national_id, username, hashed_pw.decode('utf-8')))
        self.conn.commit()
        return "ثبت نام با موفقیت انجام شد.", True

    def verify_user(self, national_id, password):
        self.cursor.execute("SELECT password_hash FROM users WHERE national_id = ?", (national_id,))
        result = self.cursor.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            return "ورود موفق", True, national_id
        return "کد ملی یا رمز عبور اشتباه است.", False, None

    def log_training_results(self, national_id, model_name, metrics):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO training_results (national_id, model_name, mae, mape, rmse, mse, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (national_id, model_name, metrics['mae'], metrics['mape'], metrics['rmse'], metrics['mse'], timestamp))
        self.conn.commit()

    def close(self):
        self.conn.close()

# --- 3 & 4. DATA PROCESSING ---
class DataProcessor:
    """Handles loading and processing of user-uploaded data."""
    def __init__(self, calendar_df):
        self.calendar_df = calendar_df

    def load_data(self, file_path):
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith(('.xls', '.xlsx')):
            return pd.read_excel(file_path)
        raise ValueError("فرمت فایل پشتیبانی نمی‌شود. لطفا CSV یا Excel آپلود کنید.")

    def process_data(self, df, date_col, value_col):
        def to_gregorian(jalali_str):
            try:
                dt_part = jalali_str.split(' - ')[0]
                y, m, d = map(int, dt_part.split('/'))
                return JalaliDate(y, m, d).to_gregorian()
            except:
                return pd.NaT

        df['gregorian_date'] = df[date_col].apply(to_gregorian)
        df = df.dropna(subset=['gregorian_date'])
        df = df.set_index('gregorian_date')

        daily_df = df[value_col].resample('D').mean().to_frame()

        if len(daily_df) > 100000:
            daily_df = daily_df.tail(100000)

        daily_df[value_col] = daily_df[value_col].ffill().bfill()
        if daily_df[value_col].isnull().any():
             daily_df[value_col] = daily_df[value_col].fillna(daily_df[value_col].mean())

        daily_df.index = daily_df.index.normalize()
        merged_df = pd.merge(daily_df, self.calendar_df, left_index=True, right_on='date', how='left')

        for col in ['is_friday', 'is_national_holiday', 'is_religious_holiday']:
            if col not in merged_df.columns:
                merged_df[col] = 0
            merged_df[col] = merged_df[col].fillna(0)

        merged_df = merged_df.set_index('date')
        return merged_df

# --- 5, 6, 7. MODELING & FORECASTING ---
class ModelHandler:
    """Handles model training, fine-tuning, and prediction."""
    def __init__(self, user_national_id):
        self.national_id = user_national_id
        self.user_model_dir = os.path.join("./user_data", self.national_id)
        os.makedirs(self.user_model_dir, exist_ok=True)

    def get_model_path(self, model_name):
        filename = f"model_{model_name.lower()}{MODEL_CONFIG[model_name]['ext']}"
        return os.path.join(self.user_model_dir, filename)

    def _create_sequences(self, data, n_steps):
        X, y = [], []
        for i in range(len(data)):
            end_ix = i + n_steps
            if end_ix > len(data)-1:
                break
            seq_x, seq_y = data[i:end_ix, :], data[end_ix, 0]
            X.append(seq_x)
            y.append(seq_y)
        return np.array(X), np.array(y)

    def train_model(self, model_name, data, fine_tune, progress_callback):
        model_path = self.get_model_path(model_name)
        features = [col for col in data.columns if col not in ['description', 'date']]
        target_col = features[0]

        X = data[features].values
        y = data[target_col].values

        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)

        if model_name == "XGBoost":
            progress_callback("در حال آموزش مدل XGBoost...")
            model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
            if fine_tune and os.path.exists(model_path):
                model.load_model(model_path)

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=10, verbose=False)

            model.save_model(model_path)
            preds = model.predict(X_test)

        else: # Keras models
            n_steps = 30
            X_seq, y_seq = self._create_sequences(X_scaled, n_steps)
            X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.2, shuffle=False)

            model = None
            if fine_tune and os.path.exists(model_path):
                progress_callback(f"در حال بارگذاری مدل {model_name} برای فاین‌تیون...")
                model = load_model(model_path)
            else:
                progress_callback(f"در حال ساخت مدل {model_name} از ابتدا...")
                n_features = X_seq.shape[2]
                model = Sequential()
                if model_name == "RNN":
                    model.add(LSTM(50, activation='relu', input_shape=(n_steps, n_features)))
                elif model_name == "GRU":
                    model.add(GRU(50, activation='relu', input_shape=(n_steps, n_features)))
                elif model_name == "CNN1D":
                    model.add(Conv1D(filters=64, kernel_size=2, activation='relu', input_shape=(n_steps, n_features)))
                    model.add(MaxPooling1D(pool_size=2))
                    model.add(Flatten())
                model.add(Dense(1))
                model.compile(optimizer='adam', loss='mse')

            early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
            progress_callback(f"در حال آموزش مدل {model_name}...")
            model.fit(X_train, y_train, epochs=50, validation_data=(X_test, y_test),
                      callbacks=[early_stopping], verbose=0)
            model.save(model_path)

            preds_scaled = model.predict(X_test)
            dummy_preds = np.zeros((len(preds_scaled), X_scaled.shape[1]))
            dummy_preds[:, 0] = preds_scaled.ravel()
            preds = scaler.inverse_transform(dummy_preds)[:, 0]

            dummy_y_test = np.zeros((len(y_test), X_scaled.shape[1]))
            dummy_y_test[:, 0] = y_test.ravel()
            y_test = scaler.inverse_transform(dummy_y_test)[:, 0]

        mae = mean_absolute_error(y_test, preds)
        mse = mean_squared_error(y_test, preds)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((y_test - preds) / y_test)) * 100 if np.all(y_test != 0) else float('inf')

        metrics = {'mae': mae, 'mse': mse, 'rmse': rmse, 'mape': mape, 'preds': preds, 'y_test': y_test}
        progress_callback("آموزش کامل شد.")
        return metrics

    def predict(self, model_name, data, horizon_days):
        model_path = self.get_model_path(model_name)
        if not os.path.exists(model_path):
            raise FileNotFoundError("ابتدا باید مدل را آموزش دهید.")

        features = [col for col in data.columns if col not in ['description', 'date']]

        last_date = data.index[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon_days)

        future_df = pd.DataFrame(index=future_dates)
        future_df['date'] = future_df.index

        merged_future = pd.merge(future_df, calendar_df, on='date', how='left').fillna(0)

        predictions = []

        if model_name == "XGBoost":
            model = xgb.XGBRegressor()
            model.load_model(model_path)
            last_consumption = data[features[0]].iloc[-1]

            for i in range(horizon_days):
                future_features = merged_future.iloc[i]
                current_features = np.array([
                    last_consumption,
                    future_features['is_friday'],
                    future_features['is_national_holiday'],
                    future_features['is_religious_holiday']
                ]).reshape(1, -1)

                pred = model.predict(current_features)[0]
                predictions.append(pred)
                last_consumption = pred

        else: # Keras models
            scaler = MinMaxScaler()
            scaler.fit(data[features].values)
            scaled_data = scaler.transform(data[features].values)

            model = load_model(model_path)
            n_steps = 30
            last_sequence = scaled_data[-n_steps:]

            for i in range(horizon_days):
                pred_scaled = model.predict(last_sequence.reshape(1, n_steps, len(features)))[0][0]

                dummy_pred = np.zeros((1, len(features)))
                dummy_pred[0, 0] = pred_scaled
                pred = scaler.inverse_transform(dummy_pred)[0, 0]
                predictions.append(pred)

                future_features = merged_future.iloc[i]
                next_feature_row = np.array([
                    pred,
                    future_features['is_friday'],
                    future_features['is_national_holiday'],
                    future_features['is_religious_holiday']
                ])

                scaled_next_row = scaler.transform(next_feature_row.reshape(1,-1))
                last_sequence = np.append(last_sequence[1:], scaled_next_row, axis=0)

        return np.array(predictions)


# --- GUI COMPONENTS ---
class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.db_manager = app_instance.db_manager

        self.font = ("Vazirmatn", 14)

        self.tabview = ctk.CTkTabview(self, width=350, height=300)
        self.tabview.pack(pady=20, padx=20)
        self.tabview.add(get_display("ورود"))
        self.tabview.add(get_display("ثبت نام"))

        self._create_login_tab(self.tabview.tab(get_display("ورود")))
        self._create_register_tab(self.tabview.tab(get_display("ثبت نام")))

    def _create_login_tab(self, tab):
        self.login_nid_label = ctk.CTkLabel(tab, text=get_display("کد ملی"), font=self.font)
        self.login_nid_label.pack(pady=(20, 5))
        self.login_nid_entry = ctk.CTkEntry(tab, width=200, justify='right')
        self.login_nid_entry.pack()

        self.login_pass_label = ctk.CTkLabel(tab, text=get_display("رمز عبور"), font=self.font)
        self.login_pass_label.pack(pady=5)
        self.login_pass_entry = ctk.CTkEntry(tab, width=200, show='*', justify='right')
        self.login_pass_entry.pack()

        self.login_button = ctk.CTkButton(tab, text=get_display("ورود"), font=self.font, command=self.login_event)
        self.login_button.pack(pady=20)

    def _create_register_tab(self, tab):
        self.reg_nid_label = ctk.CTkLabel(tab, text=get_display("کد ملی (۱۰ رقمی)"), font=self.font)
        self.reg_nid_label.pack(pady=(20, 5))
        self.reg_nid_entry = ctk.CTkEntry(tab, width=200, justify='right')
        self.reg_nid_entry.pack()

        self.reg_user_label = ctk.CTkLabel(tab, text=get_display("نام کاربری"), font=self.font)
        self.reg_user_label.pack(pady=5)
        self.reg_user_entry = ctk.CTkEntry(tab, width=200, justify='right')
        self.reg_user_entry.pack()

        self.reg_pass_label = ctk.CTkLabel(tab, text=get_display("رمز عبور"), font=self.font)
        self.reg_pass_label.pack(pady=5)
        self.reg_pass_entry = ctk.CTkEntry(tab, width=200, show='*', justify='right')
        self.reg_pass_entry.pack()

        self.register_button = ctk.CTkButton(tab, text=get_display("ثبت نام"), font=self.font, command=self.register_event)
        self.register_button.pack(pady=20)

    def login_event(self):
        nid = self.login_nid_entry.get()
        pwd = self.login_pass_entry.get()
        msg, success, national_id = self.db_manager.verify_user(nid, pwd)
        if success:
            show_persian_message("موفق", msg)
            self.app.show_dashboard(national_id)
        else:
            show_persian_message("خطا", msg, "error")

    def register_event(self):
        nid = self.reg_nid_entry.get()
        user = self.reg_user_entry.get()
        pwd = self.reg_pass_entry.get()
        msg, success = self.db_manager.register_user(nid, user, pwd)
        if success:
            show_persian_message("موفق", msg)
            self.tabview.set(get_display("ورود"))
        else:
            show_persian_message("خطا", msg, "error")


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance, national_id):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.national_id = national_id
        self.data_processor = DataProcessor(calendar_df)
        self.model_handler = ModelHandler(national_id)
        self.font = ("Vazirmatn", 12)
        self.processed_data = None
        self.fig = None
        self.canvas = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._create_control_panel()
        self._create_display_panel()

    def _create_control_panel(self):
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- 1. Data Upload ---
        data_frame = ctk.CTkFrame(panel)
        data_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(data_frame, text=get_display("۱. بارگذاری و پردازش داده"), font=(self.font[0], 14, "bold")).pack(pady=5)

        self.upload_btn = ctk.CTkButton(data_frame, text=get_display("انتخاب فایل (CSV/Excel)"), font=self.font, command=self.upload_file)
        self.upload_btn.pack(pady=5, fill="x")
        self.file_label = ctk.CTkLabel(data_frame, text=get_display("فایلی انتخاب نشده"), font=self.font, wraplength=200)
        self.file_label.pack(pady=5)

        ctk.CTkLabel(data_frame, text=get_display("ستون تاریخ (فرمت: YYYY/MM/DD - HH:MM:SS)"), font=self.font).pack()
        self.date_col_entry = ctk.CTkEntry(data_frame, justify='right')
        self.date_col_entry.pack(pady=(0,5))

        ctk.CTkLabel(data_frame, text=get_display("ستون مصرف آب"), font=self.font).pack()
        self.value_col_entry = ctk.CTkEntry(data_frame, justify='right')
        self.value_col_entry.pack(pady=(0,10))

        self.process_btn = ctk.CTkButton(data_frame, text=get_display("پردازش داده‌ها"), font=self.font, command=self.process_data_thread, state="disabled")
        self.process_btn.pack(pady=5, fill="x")

        # --- 2. Model Training ---
        train_frame = ctk.CTkFrame(panel)
        train_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(train_frame, text=get_display("۲. آموزش مدل"), font=(self.font[0], 14, "bold")).pack(pady=5)

        self.model_menu = ctk.CTkOptionMenu(train_frame, values=list(MODEL_CONFIG.keys()), font=self.font)
        self.model_menu.pack(pady=5, fill="x")

        self.train_btn = ctk.CTkButton(train_frame, text=get_display("آموزش / فاین‌تیون مدل"), font=self.font, command=self.train_model_thread, state="disabled")
        self.train_btn.pack(pady=5, fill="x")

        # --- 3. Forecasting ---
        forecast_frame = ctk.CTkFrame(panel)
        forecast_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(forecast_frame, text=get_display("۳. پیش‌بینی"), font=(self.font[0], 14, "bold")).pack(pady=5)

        self.horizon_menu = ctk.CTkOptionMenu(forecast_frame, values=[get_display("۲۴ ساعت"), get_display("۴۸ ساعت"), get_display("۱ هفته")], font=self.font)
        self.horizon_menu.pack(pady=5, fill="x")

        self.predict_btn = ctk.CTkButton(forecast_frame, text=get_display("اجرای پیش‌بینی"), font=self.font, command=self.predict_thread, state="disabled")
        self.predict_btn.pack(pady=5, fill="x")

        # --- Status Label ---
        self.status_label = ctk.CTkLabel(panel, text="", font=self.font)
        self.status_label.pack(pady=10, fill="x")

    def _create_display_panel(self):
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.fig = plt.figure(figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor('#2B2B2B') # Match dark theme

        self.canvas = FigureCanvasTkAgg(self.fig, master=panel)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.canvas.draw()

    def update_status(self, text, is_error=False):
        self.status_label.configure(text=get_display(text), text_color="red" if is_error else "white")

    def set_buttons_state(self, state):
        self.upload_btn.configure(state=state)
        self.process_btn.configure(state=state if self.file_label.cget("text") != get_display("فایلی انتخاب نشده") else "disabled")
        self.train_btn.configure(state=state if self.processed_data is not None else "disabled")
        self.predict_btn.configure(state=state if self.processed_data is not None else "disabled")

    def upload_file(self):
        file_path = filedialog.askopenfilename(title=get_display("انتخاب فایل"),
                                               filetypes=[("Excel/CSV files", "*.xlsx *.xls *.csv")])
        if file_path:
            self.file_path = file_path
            self.file_label.configure(text=get_display(os.path.basename(file_path)))
            self.process_btn.configure(state="normal")

    def process_data_thread(self):
        date_col = self.date_col_entry.get()
        value_col = self.value_col_entry.get()
        if not date_col or not value_col:
            show_persian_message("خطا", "لطفا نام ستون‌های تاریخ و مصرف را وارد کنید.", "error")
            return

        self.set_buttons_state("disabled")
        self.update_status("در حال پردازش داده‌ها...")

        def task():
            try:
                df = self.data_processor.load_data(self.file_path)
                self.processed_data = self.data_processor.process_data(df, date_col, value_col)
                self.after(0, self.on_data_processed)
            except Exception as e:
                self.after(0, lambda: self.on_task_error(e))

        threading.Thread(target=task, daemon=True).start()

    def on_data_processed(self):
        self.update_status("پردازش داده کامل شد. آماده برای آموزش.")
        self.set_buttons_state("normal")
        self.plot_data(self.processed_data, self.processed_data.columns[0])
        show_persian_message("موفق", "داده‌ها با موفقیت پردازش و برای نمایش آماده شدند.")

    def train_model_thread(self):
        model_name = self.model_menu.get()
        model_path = self.model_handler.get_model_path(model_name)
        fine_tune = False

        if os.path.exists(model_path):
            dialog = ToplevelDialog(
                title="انتخاب نوع آموزش",
                question="مدل موجود یافت شد. می‌خواهید آن را فاین‌تیون کنید یا از ابتدا آموزش دهید؟",
                options=["فاین‌تیون", "آموزش از ابتدا", "انصراف"]
            )
            choice = dialog.get()

            if choice == "فاین‌تیون":
                fine_tune = True
            elif choice == "آموزش از ابتدا":
                fine_tune = False
            else: # انصراف or None
                return
        else:
            if not ask_persian_question("آموزش جدید", "مدل انتخاب‌شده موجود نیست. آیا می‌خواهید آموزش را از صفر آغاز کنید؟"):
                return

        self.set_buttons_state("disabled")

        def task():
            try:
                metrics = self.model_handler.train_model(model_name, self.processed_data, fine_tune, lambda msg: self.after(0, self.update_status, msg))
                self.app.db_manager.log_training_results(self.national_id, model_name, metrics)
                self.after(0, lambda: self.on_training_complete(metrics))
            except Exception as e:
                self.after(0, lambda: self.on_task_error(e))

        threading.Thread(target=task, daemon=True).start()

    def on_training_complete(self, metrics):
        self.update_status("آموزش مدل با موفقیت تمام شد.")
        self.set_buttons_state("normal")

        self.plot_data(data=None, value_col=None, y_true=metrics['y_test'], y_pred=metrics['preds'])

        msg = f"آموزش کامل شد.\n" \
              f"MAE: {metrics['mae']:.2f}\n" \
              f"MAPE: {metrics['mape']:.2f}%\n" \
              f"RMSE: {metrics['rmse']:.2f}"
        show_persian_message("نتایج آموزش", msg)

    def predict_thread(self):
        horizon_map = {get_display("۲۴ ساعت"): 1, get_display("۴۸ ساعت"): 2, get_display("۱ هفته"): 7}
        horizon_days = horizon_map[self.horizon_menu.get()]
        model_name = self.model_menu.get()

        self.set_buttons_state("disabled")
        self.update_status(f"در حال پیش‌بینی برای {horizon_days} روز آینده...")

        def task():
            try:
                predictions = self.model_handler.predict(model_name, self.processed_data, horizon_days)
                self.after(0, lambda: self.on_prediction_complete(predictions))
            except Exception as e:
                self.after(0, lambda: self.on_task_error(e))

        threading.Thread(target=task, daemon=True).start()

    def on_prediction_complete(self, predictions):
        self.update_status("پیش‌بینی کامل شد.")
        self.set_buttons_state("normal")
        self.plot_data(self.processed_data, self.processed_data.columns[0], predictions=predictions)
        show_persian_message("موفق", "پیش‌بینی با موفقیت انجام شد و در نمودار نمایش داده شد.")

    def on_task_error(self, error):
        print(f"Error: {error}") # For debugging
        self.update_status(f"خطا: {error}", is_error=True)
        self.set_buttons_state("normal")
        show_persian_message("خطا", str(error), "error")

    def plot_data(self, data, value_col, y_true=None, y_pred=None, predictions=None):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor('#333333')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')

        if data is not None:
            ax.plot(data.index, data[value_col], label=get_display("داده‌های واقعی"), color='cyan', alpha=0.8)

        if y_pred is not None and y_true is not None:
            ax.scatter(y_true, y_pred, alpha=0.5)
            ax.plot([min(y_true), max(y_true)], [min(y_true), max(y_true)], color='red', linestyle='--')
            ax.set_xlabel(get_display("مقادیر واقعی"), color='white', fontname='Vazirmatn', fontsize=12)
            ax.set_ylabel(get_display("مقادیر پیش‌بینی شده"), color='white', fontname='Vazirmatn', fontsize=12)
            ax.set_title(get_display("نتایج اعتبارسنجی مدل"), color='white', fontname='Vazirmatn', fontsize=14)
            ax.legend([get_display("پیش‌بینی‌ها"), get_display("خط ایده‌آل")], prop={'family': 'Vazirmatn', 'size': 10})

        if predictions is not None:
            last_date = data.index[-1]
            pred_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=len(predictions))
            ax.plot(pred_index, predictions, label=get_display("پیش‌بینی آینده"), color='red', linestyle='--')

            std_dev = np.std(predictions)
            ax.fill_between(pred_index, predictions - std_dev, predictions + std_dev, color='red', alpha=0.2, label=get_display("بازه اطمینان"))

        if not (y_pred is not None and y_true is not None):
             ax.set_xlabel(get_display("تاریخ"), color='white', fontname='Vazirmatn', fontsize=12)
             ax.set_ylabel(get_display("مصرف آب (متر مکعب)"), color='white', fontname='Vazirmatn', fontsize=12)
             ax.set_title(get_display("نمودار مصرف آب"), color='white', fontname='Vazirmatn', fontsize=14)
             ax.legend(prop={'family': 'Vazirmatn', 'size': 10})

        ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')
        self.fig.tight_layout()
        self.canvas.draw()


# --- MAIN APPLICATION ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(get_display("سامانه پیش‌بینی مصرف آب"))
        self.geometry("1200x700")
        self.resizable(True, True)

        self.db_manager = None
        self.current_frame = None
        self.national_id = None

        self.setup_dirs_db()
        self.show_login()

    def setup_dirs_db(self):
        for d in BASE_DIRS:
            os.makedirs(d, exist_ok=True)
        self.db_manager = DBManager(DB_PATH)
        self.db_manager.setup_database()

    def switch_frame(self, frame_class, *args, **kwargs):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_class(self, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

    def show_login(self):
        self.switch_frame(LoginFrame, self)

    def show_dashboard(self, national_id):
        self.national_id = national_id
        os.makedirs(os.path.join("./user_data", self.national_id), exist_ok=True)
        os.makedirs(os.path.join("./results", self.national_id), exist_ok=True)

        self.switch_frame(DashboardFrame, self, self.national_id)

    def on_closing(self):
        if self.db_manager:
            self.db_manager.close()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()