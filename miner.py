import socket
import json
import struct
import binascii
import hashlib
import time
import sys

HOST = 'sha256.na.mine.zpool.ca'
PORT = 3333
USERNAME = 'RPAwbi57Le4u5L2Kniz1ZgGYEgHdCXx3Wu.RVN'
PASSWORD = 'c=RVN'

def create_tcp_connection(host, port):
    try:
        print(f"🌐 Connecting to {host}:{port} via TCP...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((host, port))
        print(f"✅ Connected successfully to {host}:{port}!")
        return sock
    except Exception as e:
        print(f"❌ ERROR: Connection failed - {e}")
        sys.exit(1)

def receive_message(sock):
    response = ""
    try:
        while True:
            part = sock.recv(4096).decode('utf-8')
            if not part:
                print("❌ ERROR: Connection closed by server.")
                sys.exit(1)
            response += part
            if "\n" in response:
                break
    except socket.timeout:
        print("❌ ERROR: Socket timeout.")
        sys.exit(1)
    messages = response.strip().split("\n")
    parsed_messages = []
    for msg in messages:
        try:
            parsed_messages.append(json.loads(msg))
        except json.JSONDecodeError:
            print(f"❌ ERROR: Failed to parse JSON: {msg}")
    return parsed_messages

def subscribe_sha256(sock):
    print("🔗 Subscribing...")
    subscribe_msg = {
        "id": 1,
        "method": "mining.subscribe",
        "params": ["python-miner/1.0"]
    }
    sock.sendall((json.dumps(subscribe_msg) + '\n').encode())
    responses = receive_message(sock)
    for res in responses:
        if "result" in res:
            print("✅ Subscribed!")
            extranonce1 = res['result'][1]
            extranonce2_size = res['result'][2]
            return res, extranonce1, extranonce2_size
    print("❌ Subscription failed.")
    sys.exit(1)

def authorize_sha256(sock, username, password):
    print("🔑 Authorizing...")
    auth_msg = {
        "id": 2,
        "method": "mining.authorize",
        "params": [username, password]
    }
    sock.sendall((json.dumps(auth_msg) + '\n').encode())
    responses = receive_message(sock)
    for res in responses:
        if res.get("result") is True:
            print("✅ Authorized!")
            return res
    print("❌ Authorization failed.")
    sys.exit(1)

def calculate_merkle_root(coinbase_hash, merkle_branch):
    current_hash = coinbase_hash
    for h in merkle_branch:
        branch_hash = binascii.unhexlify(h)[::-1]
        combined = current_hash.digest() + branch_hash # Use digest() to get bytes from hash object
        current_hash = hashlib.sha256(hashlib.sha256(combined).digest()) # Reassign current_hash to hash object
    return binascii.hexlify(current_hash.digest()[::-1]).decode() # Use digest() and reverse for final output

def mine_sha256(sock, username, extranonce1, extranonce2_size):
    extranonce2_counter = 0
    hashes_per_second = 0  # Initialize hashrate variable
    hash_count = 0         # Counter for hashes in the current interval
    last_report_time = time.time() # Time of last hashrate report
    report_interval = 10     # Report hashrate every 10 seconds

    try:
        while True:
            messages = receive_message(sock)
            for data in messages:
                if data.get("method") == "mining.notify":
                    params = data["params"]
                    job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _ = params
                    # Generate extranonce2
                    extranonce2 = f"{extranonce2_counter:0{extranonce2_size * 2}x}"
                    extranonce2_counter += 1
                    # Build coinbase transaction
                    coinbase_tx = binascii.unhexlify(coinb1) + binascii.unhexlify(extranonce1) + binascii.unhexlify(extranonce2) + binascii.unhexlify(coinb2)
                    coinbase_hash = hashlib.sha256(hashlib.sha256(coinbase_tx).digest())
                    # Compute Merkle root
                    merkle_root_hex = calculate_merkle_root(coinbase_hash, merkle_branch)
                    merkle_root = binascii.unhexlify(merkle_root_hex)[::-1]
                    # Construct block header
                    version_bytes = struct.pack("<I", int(version, 16))
                    prevhash_bytes = binascii.unhexlify(prevhash)[::-1]
                    nbits_bytes = binascii.unhexlify(nbits)[::-1]
                    ntime_bytes = struct.pack("<I", int(ntime, 16))
                    nonce = 0
                    target = bits_to_target(nbits)
                    print(f"🔨 Mining job {job_id}, Target: {target}")
                    # Start mining
                    start_time = time.time()
                    while time.time() - start_time < 10:
                        nonce_bytes = struct.pack("<I", nonce)
                        block_header = (
                            version_bytes +
                            prevhash_bytes +
                            merkle_root +
                            ntime_bytes +
                            nbits_bytes +
                            nonce_bytes
                        )
                        # Double SHA-256
                        hash_result = hashlib.sha256(hashlib.sha256(block_header).digest()).hexdigest()
                        hash_int = int(hash_result, 16)
                        hash_count += 1  # Increment hash count for hashrate calculation
                        if hash_int < target:
                            print(f"🎉 Valid share found! Nonce: {nonce}")
                            submit_msg = {
                                "id": 4,
                                "method": "mining.submit",
                                "params": [
                                    username,
                                    job_id,
                                    extranonce2,
                                    ntime,
                                    f"{nonce:08x}"
                                ]
                            }
                            sock.sendall((json.dumps(submit_msg) + '\n').encode())
                            print("📤 Submitted share.")
                            break
                        nonce += 1

                    current_time = time.time()
                    if current_time - last_report_time >= report_interval:
                        elapsed_time = current_time - last_report_time
                        hashes_per_second = hash_count / elapsed_time
                        print(f"📊 Hashrate: {hashes_per_second:.2f} H/s") # Display Hashrate
                        hash_count = 0 # Reset hash counter
                        last_report_time = current_time # Update last report time


    except KeyboardInterrupt:
        print("⏹️ Mining stopped.")
    finally:
        sock.close()
def bits_to_target(nbits_hex):
    nbits = int(nbits_hex, 16)
    exponent = nbits >> 24
    mantissa = nbits & 0xffffff
    return mantissa << (8 * (exponent - 3))

def main_sha256():
    sock = create_tcp_connection(HOST, PORT)
    sub_res, extranonce1, extranonce2_size = subscribe_sha256(sock)
    authorize_sha256(sock, USERNAME, PASSWORD)
    mine_sha256(sock, USERNAME, extranonce1, extranonce2_size)

if __name__ == "__main__":
    main_sha256()
