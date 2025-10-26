
# miner_unmineable.py
# Stable TCP miner client for sha256.unmineable.com (TRX example)
# Usage: edit USERNAME and optionally HOST/PORT, then run `python3 miner_unmineable.py` on your VPS.

import socket, json, binascii, hashlib, struct, time, sys

# --- CONFIGURATION (edit these) ---
HOST = 'sha256.sea.mine.zpool.ca:'
PORT = 3333
USERNAME = 'DL1QPkjfS5marmWc38jNKRSpGBUEKoyspf'  # <-- change if needed
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

def receive_messages(sock):
    data = ''
    try:
        while True:
            part = sock.recv(4096).decode('utf-8', errors='ignore')
            if not part:
                # remote closed
                raise ConnectionResetError('Connection closed by remote host')
            data += part
            if '\\n' in data:
                break
    except socket.timeout:
        # return empty to allow loop to continue and attempt reconnect or wait
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

def subscribe(sock):
    msg = { "id": 1, "method": "mining.subscribe", "params": ["python-miner/1.0"] }
    sock.sendall((json.dumps(msg) + '\\n').encode())
    return

def authorize(sock):
    msg = { "id": 2, "method": "mining.authorize", "params": [USERNAME, PASSWORD] }
    sock.sendall((json.dumps(msg) + '\\n').encode())
    return

def bits_to_target(nbits_hex):
    nbits = int(nbits_hex, 16)
    exponent = nbits >> 24
    mantissa = nbits & 0xffffff
    return mantissa << (8 * (exponent - 3))

def calc_merkle_root(coinbase_hash_obj, merkle_branch):
    current = coinbase_hash_obj
    for h in merkle_branch:
        bh = binascii.unhexlify(h)[::-1]
        combined = current.digest() + bh
        current = hashlib.sha256(hashlib.sha256(combined).digest())
    return binascii.hexlify(current.digest()[::-1]).decode()

def mine_loop(sock):
    extranonce1 = None
    extranonce2_size = None
    try:
        # After subscribe/authorize server usually sends responses / notifications.
        while True:
            messages = receive_messages(sock)
            if not messages:
                # no messages received (timeout), allow loop to continue and keep connection
                continue
            for msg in messages:
                # handle subscription responses
                if msg.get('id') == 1 and 'result' in msg:
                    res = msg['result']
                    # result is typically [<subscriptions>, extranonce1, extranonce2_size]
                    if isinstance(res, list) and len(res) >= 3:
                        extranonce1 = res[1]
                        extranonce2_size = res[2]
                        print(f\"📡 Subscribed. extranonce1={extranonce1}, extranonce2_size={extranonce2_size}\")
                elif msg.get('id') == 2:
                    if msg.get('result') is True:
                        print(\"🔑 Authorized!\")
                    else:
                        print(\"❌ Authorization failed: \", msg)
                elif msg.get('method') == 'mining.notify':
                    params = msg.get('params', [])
                    try:
                        job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _ = params
                    except Exception:
                        print('⚠️ Unexpected notify params:', params)
                        continue
                    extranonce2_counter = 0
                    target = bits_to_target(nbits)
                    print(f\"🔨 New job {job_id}, target={target}\")
                    # Build coinbase once per extranonce2 attempt
                    while True:
                        extranonce2 = f\"{extranonce2_counter:0{(extranonce2_size or 4)*2}x}\"
                        coinbase_tx = binascii.unhexlify(coinb1) + binascii.unhexlify(extranonce1 or '') + binascii.unhexlify(extranonce2) + binascii.unhexlify(coinb2)
                        coinbase_hash = hashlib.sha256(hashlib.sha256(coinbase_tx).digest())
                        merkle_root_hex = calc_merkle_root(coinbase_hash, merkle_branch)
                        merkle_root = binascii.unhexlify(merkle_root_hex)[::-1]
                        version_bytes = struct.pack('<I', int(version, 16))
                        prevhash_bytes = binascii.unhexlify(prevhash)[::-1]
                        nbits_bytes = binascii.unhexlify(nbits)[::-1]
                        ntime_bytes = struct.pack('<I', int(ntime, 16))
                        nonce = 0
                        start_time = time.time()
                        # short mining loop to avoid locking CPU for too long; this is illustrative only
                        while time.time() - start_time < 5:
                            nonce_bytes = struct.pack('<I', nonce)
                            header = version_bytes + prevhash_bytes + merkle_root + ntime_bytes + nbits_bytes + nonce_bytes
                            digest = hashlib.sha256(hashlib.sha256(header).digest()).hexdigest()
                            if int(digest, 16) < target:
                                print(f\"🎉 Share found! nonce={nonce}, submitting...\")
                                submit_msg = {"id": 4, "method": "mining.submit", "params": [USERNAME, job_id, extranonce2, ntime, f\"{nonce:08x}\"]}
                                sock.sendall((json.dumps(submit_msg) + '\\n').encode())
                                break
                            nonce += 1
                        extranonce2_counter += 1
                        # after trying a batch, break to listen for new notifies
                        break
    except Exception as e:
        raise e

def main():
    while True:
        sock = create_connection()
        try:
            subscribe(sock)
            authorize(sock)
            mine_loop(sock)
        except Exception as e:
            print(f\"❌ Error in mining loop: {e}\")
        finally:
            try:
                sock.close()
            except:
                pass
            print(f\"🔁 Reconnecting in {RECONNECT_DELAY}s ...\\n\")
            time.sleep(RECONNECT_DELAY)

if __name__ == '__main__':
    main()
