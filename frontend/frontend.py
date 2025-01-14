import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QLineEdit, QWidget, QFileDialog, QTextEdit, QMessageBox, QHBoxLayout
)
import time

API_BASE_URL = "http://127.0.0.1:5003"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Math Test Manager")
        self.setGeometry(100, 100, 800, 600)

        self.contract_address = None
        self.wallet_pem = None

        self.main_layout = QVBoxLayout()

        self.contract_label = QLabel("Contract Address:")
        self.contract_input = QLineEdit()

        self.wallet_label = QLabel("Wallet PEM: Not Uploaded")
        self.wallet_button = QPushButton("Upload PEM File")
        self.wallet_button.clicked.connect(self.upload_pem_file)

        self.set_config_button = QPushButton("Set Config")
        self.set_config_button.clicked.connect(self.set_config)

        self.sender_label = QLabel("Sender Address:")
        self.sender_input = QLineEdit()

        self.generate_test_button = QPushButton("Generate Test")
        self.generate_test_button.clicked.connect(self.generate_test)

        self.answer_inputs = [QLineEdit() for _ in range(5)]
        answers_layout = QHBoxLayout()
        for i, input_field in enumerate(self.answer_inputs):
            input_field.setPlaceholderText(f"Answer {i + 1}")
            answers_layout.addWidget(input_field)

        self.submit_test_button = QPushButton("Submit Test")
        self.submit_test_button.clicked.connect(self.submit_test)

        self.tx_hash_label = QLabel("Transaction Hash:")
        self.tx_hash_input = QLineEdit()

        self.get_operations_button = QPushButton("Get Operations")
        self.get_operations_button.clicked.connect(self.get_operations)

        self.get_correct_answers_button = QPushButton("Get Correct Answers")
        self.get_correct_answers_button.clicked.connect(self.get_correct_answers)

        self.get_test_results_button = QPushButton("Get Current Final Score")
        self.get_test_results_button.clicked.connect(self.get_test_results)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.main_layout.addWidget(self.contract_label)
        self.main_layout.addWidget(self.contract_input)
        self.main_layout.addWidget(self.wallet_label)
        self.main_layout.addWidget(self.wallet_button)
        self.main_layout.addWidget(self.set_config_button)
        self.main_layout.addWidget(self.sender_label)
        self.main_layout.addWidget(self.sender_input)
        self.main_layout.addWidget(self.generate_test_button)
        self.main_layout.addLayout(answers_layout)
        self.main_layout.addWidget(self.submit_test_button)
        self.main_layout.addWidget(self.tx_hash_label)
        self.main_layout.addWidget(self.tx_hash_input)
        self.main_layout.addWidget(self.get_operations_button)
        self.main_layout.addWidget(self.get_correct_answers_button)
        self.main_layout.addWidget(self.get_test_results_button)
        self.main_layout.addWidget(self.log_output)

        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

    def log_message(self, message):
        self.log_output.append(message)

    def upload_pem_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Wallet PEM File", "", "PEM Files (*.pem)")
        if file_path:
            with open(file_path, "r") as file:
                self.wallet_pem = file.read()
            self.wallet_label.setText(f"Wallet PEM: {file_path}")

    def set_config(self):
        self.contract_address = self.contract_input.text().strip()
        if not self.contract_address or not self.wallet_pem:
            QMessageBox.critical(self, "Error", "Please provide a contract address and upload a wallet PEM file.")
            return

        try:
            response = requests.post(f"{API_BASE_URL}/set_config", json={
                "contract_address": self.contract_address,
                "wallet_pem": self.wallet_pem
            })
            response.raise_for_status()
            self.log_message("Configuration set successfully.")
            self.generate_test_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def generate_test(self):
        sender_address = self.sender_input.text().strip()
        if not sender_address:
            QMessageBox.critical(self, "Error", "Please provide a sender address.")
            return

        try:
            response = requests.post(f"{API_BASE_URL}/generate_and_get_operations", json={"sender_address": sender_address})
            time.sleep(30)
            response.raise_for_status()
            operations = response.json().get("operations", [])
            tx_hash = response.json().get("tx_hash")
            self.tx_hash_input.setText(tx_hash)
            self.log_message("Test generated successfully:")
            for op in operations:
                self.log_message(f"-> {op['operation']}")
            self.submit_test_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def submit_test(self):
        sender_address = self.sender_input.text().strip()
        if not sender_address:
            QMessageBox.critical(self, "Error", "Please provide a sender address.")
            return

        try:
            # Collect answers from the input fields
            answers = []
            for input_field in self.answer_inputs:
                value = input_field.text().strip()
                if not value:
                    QMessageBox.critical(self, "Error", "All answer fields must be filled.")
                    return
                try:
                    answers.append(int(value))
                except ValueError:
                    QMessageBox.critical(self, "Error", "All answers must be integers.")
                    return

            # Ensure exactly 5 answers
            if len(answers) != 5:
                QMessageBox.critical(self, "Error", "Please provide exactly 5 answers.")
                return

            # Make the API call
            response = requests.post(f"{API_BASE_URL}/submit_test", json={
                "sender_address": sender_address,
                "answers": answers
            })
            time.sleep(30)  # Wait for the transaction to process
            response.raise_for_status()
            result = response.json()
            tx_hash = result.get("tx_hash")
            self.tx_hash_input.setText(tx_hash)
            self.log_message(f"Test submitted: {result.get('correct_answers', 'No result')} correct answers.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


    def get_operations(self):
        tx_hash = self.tx_hash_input.text().strip()
        if not tx_hash:
            QMessageBox.critical(self, "Error", "Please provide a transaction hash.")
            return

        try:
            response = requests.get(f"{API_BASE_URL}/get_operations", params={"tx_hash": tx_hash})
            response.raise_for_status()
            operations = response.json().get("operations", [])
            self.log_message("Operations fetched successfully:")
            for op in operations:
                self.log_message(f"-> {op['operation']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_correct_answers(self):
        tx_hash = self.tx_hash_input.text().strip()
        if not tx_hash:
            QMessageBox.critical(self, "Error", "Please provide a transaction hash.")
            return

        try:
            response = requests.get(f"{API_BASE_URL}/get_correct_answers", params={"tx_hash": tx_hash})
            response.raise_for_status()
            correct_answers = response.json().get("correct_answers", "No result")
            self.log_message(f"Correct answers: {correct_answers}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_test_results(self):
        contract_address = self.contract_input.text().strip()
        sender_address = self.sender_input.text().strip()

        if not contract_address or not sender_address:
            QMessageBox.critical(self, "Error", "Please provide both the contract address and sender address.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/get_test_results",
                json={
                    "contract_address": contract_address,
                    "user_address": sender_address,
                }
            )
            response.raise_for_status()
            test_results = response.json().get("test_results", "No result")
            self.log_message(f"Final Score: {test_results}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
