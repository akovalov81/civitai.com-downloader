import sys
import os
import requests
import time
import random
import webbrowser
import json
from urllib.parse import urlparse, parse_qsl
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QLineEdit, QPushButton, QFileDialog,
                           QMessageBox, QDesktopWidget, QTextEdit, QProgressBar,
                           QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

# Клас для виконання завантаження в окремому потоці
class DownloadThread(QThread):
    # Сигнали для оновлення інтерфейсу
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, api_key, model_id, model_version_id, download_folder, image_limit=100, nsfw='X'):
        QThread.__init__(self)
        self.api_key = api_key
        self.model_id = model_id
        self.model_version_id = model_version_id
        self.download_folder = download_folder
        self.image_limit = image_limit
        self.nsfw = nsfw
        self.is_running = True
        
    def run(self):
        try:
            self.download_images()
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(f"Помилка: {str(e)}")
    
    def stop(self):
        self.is_running = False
    
    def download_images(self):
        base_url = "https://civitai.com/api/v1/images"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        params = {
            "limit": self.image_limit,
            "modelId": self.model_id,
            "modelVersionId": self.model_version_id if self.model_version_id else None,
            "nsfw": self.nsfw,
            "sort": "Most Reactions"
        }

        # Видалити None значення з параметрів
        params = {k: v for k, v in params.items() if v is not None}
        next_page_url = None

        while self.is_running:
            url = next_page_url if next_page_url else base_url
            self.progress_signal.emit(f"Запит до: {url}")
            
            response = requests.get(url, headers=headers, params=params if not next_page_url else {})
            if response.status_code != 200:
                self.progress_signal.emit(f"Помилка: {response.status_code} - {response.text}")
                break

            data = response.json()
            items = data.get("items", [])

            if not items:
                self.progress_signal.emit("Більше немає зображень для завантаження.")
                break

            # Підготувати директорію
            model_dir = os.path.join(self.download_folder, str(self.model_id))
            os.makedirs(model_dir, exist_ok=True)

            if self.model_version_id:
                model_dir = os.path.join(model_dir, str(self.model_version_id))
                os.makedirs(model_dir, exist_ok=True)

            for item in items:
                if not self.is_running:
                    break
                    
                image_url = item.get("url")
                meta = item.get("meta") or {}
                prompt = meta.get("prompt", "Підказка недоступна.")

                if image_url:
                    # Витягти ім'я файлу зображення
                    parsed_url = urlparse(image_url)
                    image_name = os.path.basename(parsed_url.path)
                    image_path = os.path.join(model_dir, image_name)

                    # Перевірити, чи зображення вже існує
                    if os.path.exists(image_path):
                        self.progress_signal.emit(f"Зображення вже існує, пропускаємо: {image_name}")
                        continue

                    # Завантажити зображення
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        with open(image_path, "wb") as img_file:
                            img_file.write(img_response.content)
                        self.progress_signal.emit(f"Завантажено зображення: {image_name}")

                        # Зберегти підказку
                        prompt_path = os.path.join(model_dir, f"{os.path.splitext(image_name)[0]}.txt")
                        with open(prompt_path, "w", encoding="utf-8") as prompt_file:
                            prompt_file.write(prompt)
                        self.progress_signal.emit(f"Збережено підказку для: {image_name}")
                    else:
                        self.progress_signal.emit(f"Не вдалося завантажити зображення: {image_url}")

                    # Випадкова затримка, щоб уникнути блокування сервера
                    delay = random.randint(3, 8)  # Зменшено для тестування
                    self.progress_signal.emit(f"Очікування {delay} секунд перед наступним завантаженням...")
                    time.sleep(delay)

            # Перейти до наступної сторінки, якщо доступно
            next_page_url = data.get("metadata", {}).get("nextPage")
            if not next_page_url:
                break

class DownloadApp(QWidget):
    def __init__(self):
        super().__init__()
        self.download_folder = ""
        self.api_key = ""
        self.model_id = ""
        self.model_version_id = ""
        self.image_limit = 100
        self.nsfw = 'X'  # За замовчуванням включено
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "civitai_settings.json")
        self.download_thread = None
        
        # Спочатку завантажуємо налаштування, потім ініціалізуємо інтерфейс
        self.load_settings_data()  # Тільки завантажуємо дані
        self.init_ui()  # Ініціалізуємо UI з попередньо завантаженими даними
        
        # Встановлюємо значення в поля після того, як інтерфейс ініціалізовано
        self.apply_settings_to_ui()
        
        print("Програма ініціалізована")

    def init_ui(self):
        # Налаштування головного вікна
        self.setWindowTitle('Додаток для завантаження зображень з Civitai')
        self.setFixedSize(600, 600)
        
        # Встановлення іконки програми
        self.setWindowIcon(QIcon('e:\\Project\\5000x5000_faviconC-2048x2048.png'))
        
        # Розміщення вікна по центру екрану
        self.center_on_screen()
        
        # Створення головного вертикального лейауту
        main_layout = QVBoxLayout()
        
        # 1. Поле для вибору папки
        folder_layout = QHBoxLayout()
        folder_label = QLabel('download folder:')
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        browse_button = QPushButton('Огляд')
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)
        
        # 2. Поле для введення API ключа
        api_layout = QHBoxLayout()
        api_label = QLabel('api key:')
        self.api_input = QLineEdit()
        self.api_input.setText("12345678901234567890123456789012")  # Заповнено за замовчуванням
        self.api_input.textChanged.connect(self.check_fields)
        help_button = QPushButton('Допомога')
        help_button.clicked.connect(self.open_api_help)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(help_button)
        
        # 3. Поле для введення ID моделі
        model_layout = QHBoxLayout()
        model_label = QLabel('model id:')
        self.model_input = QLineEdit()
        self.model_input.textChanged.connect(self.check_fields)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_input)
        
        # 4. Поле для введення версії моделі
        version_layout = QHBoxLayout()
        version_label = QLabel('model version id:')
        self.version_input = QLineEdit()
        self.version_input.textChanged.connect(self.check_fields)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_input)
        
        # Додаємо поле NSFW з перемикачем
        nsfw_layout = QHBoxLayout()
        nsfw_layout.setAlignment(Qt.AlignLeft)  # Вирівнювання по лівій стороні
        nsfw_label = QLabel('NSFW:')
        self.nsfw_checkbox = QCheckBox('Включити контент для дорослих')
        self.nsfw_checkbox.setChecked(True)  # За замовчуванням включено
        self.nsfw_checkbox.stateChanged.connect(self.update_nsfw)
        
        nsfw_layout.addWidget(nsfw_label)
        nsfw_layout.addWidget(self.nsfw_checkbox)
        nsfw_layout.addStretch(1)  # Додаємо відступ справа, щоб вирівняти компоненти ліворуч
        
        # 5. Поле для вибору кількості зображень
        limit_layout = QHBoxLayout()
        limit_label = QLabel('кількість зображень:')
        self.limit_input = QSpinBox()
        self.limit_input.setRange(1, 1000)
        self.limit_input.setValue(100)
        self.limit_input.setSingleStep(10)
        
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(self.limit_input)
        
        # Лог процесу завантаження
        log_label = QLabel('Лог завантаження:')
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Прогрес-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неперервний прогрес-бар
        self.progress_bar.setVisible(False)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.download_button = QPushButton('Почати завантаження')
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        
        self.stop_button = QPushButton('Зупинити')
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setEnabled(False)
        
        self.save_settings_button = QPushButton('Зберегти налаштування')
        self.save_settings_button.clicked.connect(self.save_settings)
        
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.save_settings_button)
        
        # Додавання всіх елементів у головний лейаут
        main_layout.addLayout(folder_layout)
        main_layout.addLayout(api_layout)
        main_layout.addLayout(model_layout)
        main_layout.addLayout(version_layout)
        main_layout.addLayout(nsfw_layout)
        main_layout.addLayout(limit_layout)
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_output)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        print("Інтерфейс створено")
    
    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def open_api_help(self):
        webbrowser.open("https://github.com/civitai/civitai/wiki/REST-API-Reference")
        self.log_output.append("Відкрито веб-сторінку з довідкою по API.")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Виберіть папку для завантаження')
        if folder:
            self.download_folder = folder
            self.folder_input.setText(folder)
            self.check_fields()
    
    def update_nsfw(self, state):
        self.nsfw = 'X' if state == Qt.Checked else 'none'
    
    def check_fields(self):
        # Отримання тексту з усіх полів, але зберігаємо існуючі значення якщо вони є
        self.api_key = self.api_input.text()
        
        # Зберігаємо поточні значення
        current_model_id = self.model_id
        current_version_id = self.model_version_id
        
        # Отримуємо нові значення з полів
        new_model_id = self.model_input.text()
        new_version_id = self.version_input.text()
        
        # Оновлюємо тільки якщо нові значення не порожні або якщо поточні значення пусті
        if new_model_id:
            self.model_id = new_model_id
        elif not current_model_id and new_model_id:  # Якщо поточного значення немає, але є нове
            self.model_id = new_model_id
            
        if new_version_id:
            self.model_version_id = new_version_id
        elif not current_version_id and new_version_id:  # Якщо поточного значення немає, але є нове
            self.model_version_id = new_version_id
            
        self.image_limit = self.limit_input.value()
        
        # Перевірка заповнення всіх полів
        if (self.download_folder and self.api_key and 
            self.model_id and self.model_version_id.strip() != ""):
            self.download_button.setEnabled(True)
        else:
            self.download_button.setEnabled(False)

    def save_settings(self):
        settings = {
            "download_folder": self.download_folder,
            "api_key": self.api_key,
            "model_id": self.model_id,
            "model_version_id": self.model_version_id,
            "image_limit": self.image_limit,
            "nsfw": self.nsfw
        }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
            self.log_output.append("Налаштування збережено!")
            QMessageBox.information(self, 'Налаштування', 'Налаштування успішно збережено!')
        except Exception as e:
            self.log_output.append(f"Помилка збереження налаштувань: {str(e)}")
            QMessageBox.critical(self, 'Помилка', f'Помилка збереження налаштувань: {str(e)}')
    
    def load_settings_data(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                print(f"Завантажено налаштування: {settings}")
                
                self.download_folder = settings.get("download_folder", "")
                self.api_key = settings.get("api_key", "")
                self.model_id = settings.get("model_id", "")
                self.model_version_id = settings.get("model_version_id", "")
                self.image_limit = settings.get("image_limit", 100)
                self.nsfw = settings.get("nsfw", "X")
                
                print(f"Дані завантажено - Model ID: {self.model_id}, Version ID: {self.model_version_id}")
            except Exception as e:
                print(f"Помилка завантаження налаштувань: {str(e)}")
    
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                # Переконаємося, що у нас є найновіші дані
                self.load_settings_data()
                
                # Встановлюємо дані в інтерфейс НАПРЯМУ, минаючи сигнали
                self.folder_input.blockSignals(True)
                self.api_input.blockSignals(True)
                self.model_input.blockSignals(True)
                self.version_input.blockSignals(True)
                self.limit_input.blockSignals(True)
                
                # Встановлення значень
                if self.download_folder:
                    self.folder_input.setText(self.download_folder)
                if self.api_key:
                    self.api_input.setText(self.api_key)
                if self.model_id:
                    self.model_input.setText(self.model_id)
                if self.model_version_id:
                    self.version_input.setText(self.model_version_id)
                
                self.limit_input.setValue(self.image_limit)
                self.nsfw_checkbox.setChecked(self.nsfw == 'X')
                
                # Відновлення сигналів
                self.folder_input.blockSignals(False)
                self.api_input.blockSignals(False)
                self.model_input.blockSignals(False)
                self.version_input.blockSignals(False)
                self.limit_input.blockSignals(False)
                
                # Додаємо лаконічне повідомлення про завантаження налаштувань
                self.log_output.append("Налаштування завантажено!")
                
                # Примусово оновити стан кнопки
                self.check_fields()
            except Exception as e:
                self.log_output.append(f"Помилка завантаження налаштувань: {str(e)}")
                print(f"Помилка завантаження налаштувань: {str(e)}")

    def apply_settings_to_ui(self):
        """Встановлює збережені значення в поля UI"""
        # Блокуємо сигнали під час встановлення значень
        widgets = [self.folder_input, self.api_input, self.model_input, 
                  self.version_input, self.limit_input, self.nsfw_checkbox]
        
        # Блокуємо сигнали
        for widget in widgets:
            widget.blockSignals(True)
        
        # Встановлюємо значення
        self.folder_input.setText(self.download_folder)
        self.api_input.setText(self.api_key)
        
        # Важливо: встановлюємо значення ID моделі та версії ТІЛЬКИ якщо вони не пусті
        if self.model_id:
            self.model_input.setText(self.model_id)
        
        if self.model_version_id:
            self.version_input.setText(self.model_version_id)
        
        self.limit_input.setValue(self.image_limit)
        self.nsfw_checkbox.setChecked(self.nsfw == 'X')
        
        # Розблоковуємо сигнали
        for widget in widgets:
            widget.blockSignals(False)
        
        # Оновлюємо стан кнопки
        self.check_fields()
        
        # Додаємо інформацію в лог тільки при першому завантаженні
        if self.isVisible() and not hasattr(self, '_settings_applied'):
            self.log_output.append("Налаштування застосовано!")
            self._settings_applied = True

    def showEvent(self, event):
        super().showEvent(event)
        # Додатково встановлюємо значення після того, як вікно стане видимим
        QApplication.processEvents()
        self.apply_settings_to_ui()
    
    def closeEvent(self, event):
        # Показати діалогове вікно перед закриттям
        reply = QMessageBox.question(self, 'Вихід',
            "Зберегти поточні налаштування перед виходом?", 
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            self.save_settings()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()

    def start_download(self):
        # Блокування кнопок та оновлення інтерфейсу
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        self.log_output.append(f"Початок завантаження зображень.")
        self.log_output.append(f"Папка: {self.download_folder}")
        self.log_output.append(f"ID моделі: {self.model_id}")
        self.log_output.append(f"Версія моделі: {self.model_version_id if self.model_version_id else 'Не вказано'}")
        self.log_output.append(f"Ліміт зображень: {self.image_limit}")
        self.log_output.append(f"NSFW: {'Включено' if self.nsfw == 'X' else 'Вимкнено'}")
        
        # Створення та запуск потоку завантаження
        self.download_thread = DownloadThread(
            self.api_key, self.model_id, self.model_version_id, 
            self.download_folder, self.image_limit, self.nsfw
        )
        
        # Підключення сигналів
        self.download_thread.progress_signal.connect(self.update_log)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)
        
        # Запуск потоку
        self.download_thread.start()
    
    def stop_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.update_log("Зупинка завантаження...")
            self.download_thread.stop()
    
    def update_log(self, message):
        self.log_output.append(message)
        # Прокрутка до нового повідомлення
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
    
    def download_finished(self):
        self.update_log("Завантаження завершено!")
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Показати повідомлення про завершення
        QMessageBox.information(self, 'Завершено', 'Завантаження зображень завершено!')
    
    def download_error(self, error_message):
        self.update_log(f"ПОМИЛКА: {error_message}")
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Показати повідомлення про помилку
        QMessageBox.critical(self, 'Помилка', f'Сталася помилка під час завантаження:\n{error_message}')

if __name__ == '__main__':
    print(f"Шлях до Python: {sys.executable}")
    print(f"Поточна директорія: {os.getcwd()}")
    print("Запуск додатку...")
    app = QApplication(sys.argv)
    
    # Встановлення іконки програми для всього додатку
    app.setWindowIcon(QIcon('e:\\Project\\5000x5000_faviconC-2048x2048.png'))
    
    window = DownloadApp()
    window.show()
    print("Вікно відображено")
    sys.exit(app.exec_())
