from flask import Flask, jsonify, request
import requests
import time
from multiversx_sdk import (
    ProxyNetworkProvider,
    Address,
    UserSigner,
    TransactionComputer,
    TransactionsFactoryConfig,
    SmartContractTransactionsFactory,
)
from pathlib import Path
import subprocess

# Flask app initialization
app = Flask(__name__)

# Configuration
PROXY_URL = "https://devnet-gateway.multiversx.com"
CHAIN_ID = "D"

@app.route("/set_config", methods=["POST"])
def set_config():
    """
    Set the contract address and wallet PEM dynamically from the frontend.
    """
    global CONTRACT_ADDRESS, WALLET_PEM_PATH, wallet_signer, proxy, contract_address, transaction_computer, transactions_factory
    try:
        data = request.json
        CONTRACT_ADDRESS = data["contract_address"]
        wallet_pem_content = data["wallet_pem"]

        # Save wallet PEM to a temporary file
        WALLET_PEM_PATH = Path("dynamic_wallet.pem")
        with WALLET_PEM_PATH.open("w") as pem_file:
            pem_file.write(wallet_pem_content)

        # SDK Initialization
        proxy = ProxyNetworkProvider(PROXY_URL)
        contract_address = Address.from_bech32(CONTRACT_ADDRESS)
        wallet_signer = UserSigner.from_pem_file(Path(WALLET_PEM_PATH))
        transaction_computer = TransactionComputer()
        transactions_factory = SmartContractTransactionsFactory(
            TransactionsFactoryConfig(chain_id=CHAIN_ID)
        )

        return jsonify({"message": "Configuration set successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def fetch_transaction_data(tx_hash):
    """
    Fetch transaction data from the MultiversX Gateway API.
    """
    url = f"{PROXY_URL}/transaction/{tx_hash}?withResults=true"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("Failed to fetch transaction data.")
    return response.json()


def parse_operations(hex_data):
    """
    Decode a hex string of operations into a readable array of operations.
    Each operation is 6 bytes long.
    """
    operations = []
    for i in range(0, len(hex_data), 12):  # Each operation is 12 characters (6 bytes)
        segment = hex_data[i:i + 12]
        if len(segment) < 12:
            break

        # Decode operands and operator
        operand1 = int(segment[0:2], 16)
        operator = chr(int(segment[4:6], 16))  # Decode ASCII operator
        operand2 = int(segment[8:10], 16)

        # Map operator to human-readable format
        operator_display = {
            "+": "+",
            "-": "-",
            "*": "*",
            "/": "/",
        }.get(operator, "unknown")

        # Compose the full operation as a string
        operation_string = f"{operand1} {operator_display} {operand2}"

        operations.append({
            "hex_segment": segment,
            "operand1": operand1,
            "operator": operator_display,
            "operand2": operand2,
            "operation": operation_string
        })

    return operations


@app.route("/generate_and_get_operations", methods=["POST"])
def generate_and_get_operations():
    """
    Combines generating a test and fetching operations in a single endpoint.
    """
    try:
        sender_address_str = request.json["sender_address"]
        sender_address = Address.from_bech32(sender_address_str)
        account = proxy.get_account(sender_address)

        # Generate test transaction
        tx = transactions_factory.create_transaction_for_execute(
            sender=sender_address,
            contract=contract_address,
            function="generate_test",
            gas_limit=5_000_000,
        )
        tx.nonce = account.nonce
        bytes_to_sign = transaction_computer.compute_bytes_for_signing(tx)
        tx.signature = wallet_signer.sign(bytes_to_sign)

        # Send transaction
        tx_hash = proxy.send_transaction(tx)
        time.sleep(30)  # Wait for the transaction to process

        # Fetch transaction data
        data = fetch_transaction_data(tx_hash)

        # Extract operations
        sc_results = data["data"]["transaction"].get("smartContractResults", [])
        if not sc_results:
            return jsonify({"error": "No smart contract results found"}), 404

        raw_data = sc_results[0]["data"].split("@")[-1]
        print(raw_data)
        operations = parse_operations(raw_data)

        return jsonify({"message": "Test generated and operations fetched successfully", "tx_hash": tx_hash, "operations": operations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_operations", methods=["GET"])
def get_operations():
    """
    Fetch operations from a given transaction hash.
    """
    try:
        tx_hash = request.args.get("tx_hash")
        if not tx_hash:
            return jsonify({"error": "Missing 'tx_hash' parameter"}), 400

        # Fetch transaction data
        data = fetch_transaction_data(tx_hash)

        # Extract operations
        sc_results = data["data"]["transaction"].get("smartContractResults", [])
        if not sc_results:
            return jsonify({"error": "No smart contract results found"}), 404

        raw_data = sc_results[0]["data"].split("@")[-1]
        print(raw_data)
        operations = parse_operations(raw_data)

        return jsonify({"operations": operations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def answers_to_hex(answers):
    """
    Converts an array of answers to a hex string with `00` padding.
    Handles both positive and negative numbers.

    :param answers: List of integers representing the answers.
    :return: Hex string for transaction arguments.
    """
    hex_answers = ""

    for answer in answers:
        if answer < 0:
            # Handle negative numbers (2's complement for 8-bit representation)
            hex_answers += f"{(256 + answer):02x}"
        else:
            # Handle positive numbers
            hex_answers += f"{answer:02x}"

    # Append "00" padding
    hex_answers += "00"

    return hex_answers

def extract_correct_answers(tx_hash):
    """
    Fetch the transaction data and count the number of correct answers.

    :param tx_hash: The transaction hash.
    :return: Count of correct answers.
    """
    try:
        # Fetch transaction data
        url = f"{PROXY_URL}/transaction/{tx_hash}?withResults=true"
        response = requests.get(url)

        if response.status_code != 200:
            raise ValueError("Failed to fetch transaction data")

        data = response.json()
        sc_results = data["data"]["transaction"].get("smartContractResults", [])
        if not sc_results:
            raise ValueError("No smart contract results found")

        # Extract the data field and count occurrences of "Correct"
        correct_marker = "436f72726563740000000000"
        correct_count = sum(result["data"].count(correct_marker) for result in sc_results if "data" in result)

        return correct_count
    except Exception as e:
        print(f"Error extracting correct answers: {e}")
        return 0


@app.route("/submit_test", methods=["POST"])
def submit_test():
    """
    Submits answers for the math test as a hex string with a `00` padding.
    """
    try:
        sender_address_str = request.json["sender_address"]
        answers = request.json["answers"]  # Example: [1, 2, 3, 4, 5]

        # Convert answers to hex and pad with "00"
        answers_hex = answers_to_hex(answers)

        print(answers_hex)

        sender_address = Address.from_bech32(sender_address_str)
        account = proxy.get_account(sender_address)

        # Submit test transaction
        tx = transactions_factory.create_transaction_for_execute(
            sender=sender_address,
            contract=contract_address,
            function="submit_test",
            arguments=[bytes.fromhex(answers_hex)],
            gas_limit=5_000_000,
        )
        tx.nonce = account.nonce
        bytes_to_sign = transaction_computer.compute_bytes_for_signing(tx)
        tx.signature = wallet_signer.sign(bytes_to_sign)

         # Send transaction
        tx_hash = proxy.send_transaction(tx)

        # Wait for the transaction to be processed
        time.sleep(30)

        # Fetch transaction data
        correct_answers = extract_correct_answers(tx_hash)
        return jsonify({
            "message": "Test submitted successfully",
            "tx_hash": tx_hash,
            "correct_answers": f"{correct_answers}/5 correct answers"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_correct_answers", methods=["GET"])
def get_correct_answers():
    """
    Fetches the number of correct answers for a submitted test using the transaction hash.
    """
    try:
        # Parse the transaction hash from the request
        tx_hash = request.args.get("tx_hash")
        if not tx_hash:
            return jsonify({"error": "Missing 'tx_hash' parameter"}), 400

        # Fetch transaction data
        correct_answers = extract_correct_answers(tx_hash)

        return jsonify({
            "tx_hash": tx_hash,
            "correct_answers": f"{correct_answers}/5 correct answers"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_test_results", methods=["POST"])
def get_test_results():
    """
    Calls the MultiversX blockchain to query test results for a specific user.
    """
    data = request.json
    contract_address = data.get("contract_address")
    user_address = data.get("user_address")

    if not contract_address or not user_address:
        return jsonify({"error": "Both contract_address and user_address are required."}), 400

    # Command to call the mxpy CLI
    command = [
        "mxpy",
        "contract",
        "query",
        contract_address,
        "--function=test_results",
        f"--proxy={PROXY_URL}",
        f"--arguments={user_address}"
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        return jsonify({"error": f"Command failed: {result.stderr}"}), 500

    # Extract the first hexadecimal value from the output
    raw_output = result.stdout.strip()
    cleaned_hex_value = raw_output.replace("[", "").replace("]", "").replace("\"", "").strip()

    # Convert the cleaned hexadecimal value to a decimal integer
    try:
        decimal_value = int(cleaned_hex_value, 16)
        return jsonify({"test_results": decimal_value}), 200
    except ValueError as e:
        return jsonify({"error": f"Failed to parse hex value: {cleaned_hex_value}, error: {str(e)}"}), 500

if __name__ == "__main__":
    print("Starting Flask API for AssigningStudents Smart Contract...")
    app.run(debug=True, port=5003)
