
# miner_power2b.py
# Simple Stratum client template for CPU-friendly pools using power2b/yespower-like algorithms.
# NOTE: Many CPU pools expect miners to use specialized binaries (e.g., cpuminer) for performance.
# This Python script demonstrates connection, subscribe/authorize and a simple share submission flow.
# Edit the HOST/PORT/USERNAME to match your chosen pool (example defaults set as placeholders).

import socket, json, time, sys

# --- CONFIGURATION (edit these) ---
HOST = 'power2b.sea.mine.zpool.ca:'   # <-- change to the pool host you want
PORT = 6240                      # <-- change to pool port if needed
USERNAME = 'DL1QPkjfS5marmWc38jNKRSpGBUEKoyspf'  # <-- change to your wallet
PASSWORD = 'c=DOGE'
SOCKET_TIMEOUT = 60
RECONNECT_DELAY = 5
# -----------------------------------

def create_connection():
    while True:
        try:
            print(f\"🌐 Connecting to {HOST}:{PORT}...\")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((HOST, PORT))
            print(\"✅ Connected.\")
            return s
        except Exception as e:
            print(f\"❌ Connect error: {e}; retrying in {RECONNECT_DELAY}s...\")
            time.sleep(RECONNECT_DELAY)

def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj) + '\\n').encode())
    except Exception as e:
        raise e

def receive_messages(sock):
    data = ''
    try:
        while True:
            part = sock.recv(4096).decode('utf-8', errors='ignore')
            if not part:
                raise ConnectionResetError('Connection closed by remote host')
            data += part
            if '\\n' in data:
                break
    except socket.timeout:
        return []
    except Exception as e:
        raise e
    lines = [ln for ln in data.strip().split('\\n') if ln.strip()!='']
    msgs = []
    for ln in lines:
        try:
            msgs.append(json.loads(ln))
        except json.JSONDecodeError:
            print(f\"⚠️ Failed to decode JSON: {ln}\")
    return msgs

def main():
    while True:
        sock = create_connection()
        try:
            # Subscribe
            sub_msg = {\"id\":1, \"method\":\"mining.subscribe\", \"params\":[\"python-miner/1.0\"]}
            send_json(sock, sub_msg)
            # Authorize
            auth_msg = {\"id\":2, \"method\":\"mining.authorize\", \"params\":[USERNAME, PASSWORD]}
            send_json(sock, auth_msg)

            extranonce1 = None
            extranonce2_size = None

            while True:
                messages = receive_messages(sock)
                if not messages:
                    continue
                for m in messages:
                    # handle responses and notifications
                    if m.get('id') == 1 and 'result' in m:
                        res = m['result']
                        if isinstance(res, list) and len(res) >= 3:
                            extranonce1 = res[1]
                            extranonce2_size = res[2]
                            print(f\"📡 Subscribed. extranonce1={extranonce1}, extranonce2_size={extranonce2_size}\")
                    elif m.get('id') == 2:
                        if m.get('result') is True:
                            print(\"🔑 Authorized!\")
                        else:
                            print(\"❌ Authorization failed: \", m)
                    elif m.get('method') == 'mining.notify':
                        print(\"🔔 Got a mining.notify — this script is a template; a real CPU miner must compute algorithm-specific hashes.\")
                        # For power2b/yespower you usually need native code for performance.
                        # Here we simply ACK the notify and continue listening.
                        # If you have an external miner binary, you can launch it here and pipe work to it.
                        # Example: spawn subprocess that runs cpuminer with appropriate args.
                        continue
        except Exception as e:
            print(f\"❌ Error: {e}\")
        finally:
            try:
                sock.close()
            except:
                pass
            print(f\"🔁 Reconnecting in {RECONNECT_DELAY}s ...\\n\")
            time.sleep(RECONNECT_DELAY)

if __name__ == '__main__':
    main()
