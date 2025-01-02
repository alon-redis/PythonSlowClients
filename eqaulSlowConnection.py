import redis
import threading
import time
import random
import string
import argparse
import socket
from redis.connection import ConnectionPool

# Parse input arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Redis parallel connections tester")
    parser.add_argument('--host', type=str, required=True, help='Redis host')
    parser.add_argument('--port', type=int, required=True, help='Redis port')
    parser.add_argument('--data_size', type=int, default=1024, help='Size of data in bytes')
    parser.add_argument('--connections', type=int, default=10, help='Number of parallel connections')
    parser.add_argument('--slow_connections', type=int, default=0, help='Number of slow connections')
    parser.add_argument('--keys_count', type=int, required=True, help='Number of keys to populate during the first stage')
    parser.add_argument('--skip_population', action='store_true', help='Skip the population stage')
    parser.add_argument('--recv_chunk_size', type=int, default=64, help='Chunk size for socket recv in bytes')
    parser.add_argument('--recv_sleep_time', type=float, default=1.0, help='Sleep time between socket recv operations in seconds')
    parser.add_argument('--hash_fields', type=int, default=1000000, help='Number of fields in the large hash')
    parser.add_argument('--hash_field_size', type=int, default=100, help='Size of each field value in the large hash in bytes')
    return parser.parse_args()

# Generate random data of specified size
def generate_data(size):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

def populate_db(pool, keys_count, data_size, hash_fields, hash_field_size):
    """Populate the database with a specified number of keys and a large hash."""
    client = redis.Redis(connection_pool=pool)
    value = generate_data(data_size)

    for i in range(keys_count):
        key = f"key-{i}"
        client.set(key, value)

    print(f"Populated DB with {keys_count} keys.")

    # Add a large hash with configurable fields and field size
    hash_key = "large-hash"
    for i in range(hash_fields):
        field = f"field-{i}"
        field_value = generate_data(hash_field_size)
        client.hset(hash_key, field, field_value)

    print(f"Populated DB with large hash: {hash_key}, containing {hash_fields} fields (~{(hash_fields * hash_field_size) / (1024 * 1024):.2f} MB).")

def slow_reader(client_id, host, port, recv_chunk_size, recv_sleep_time):
    """Simulate a slow connection using raw sockets that performs HGETALL on a large hash."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            command = "HGETALL large-hash\r\n"
            sock.sendall(command.encode())

            # Read response in small chunks
            while True:
                chunk = sock.recv(recv_chunk_size)  # Read in small chunks
                if not chunk:
                    break
                time.sleep(recv_sleep_time)  # Delay to simulate slowness
    except Exception as e:
        print(f"Slow Client {client_id} encountered an error: {e}")

def read_db(pool, keys, metrics):
    """Perform read operations on the keys."""
    def worker(client_id, metrics, pool, keys):
        client = redis.Redis(connection_pool=pool)
        while True:
            try:
                key = random.choice(keys)
                client.get(key)

                with metrics["lock"]:
                    metrics["ops"] += 1
            except redis.ConnectionError as e:
                print(f"Client {client_id} encountered connection error: {e}")
                break

    threads = []
    for i in range(metrics["worker_count"]):
        thread = threading.Thread(target=worker, args=(i, metrics, pool, keys))
        thread.daemon = True
        threads.append(thread)
        thread.start()

    try:
        while True:
            time.sleep(1)
            with metrics["lock"]:
                ops = metrics["ops"]
                print(f"Throughput: {ops} ops/sec")
                metrics["ops"] = 0
    except KeyboardInterrupt:
        print("Shutting down...")
        for thread in threads:
            thread.join()

def main():
    args = parse_args()
    pool = ConnectionPool(host=args.host, port=args.port, max_connections=args.connections + args.slow_connections)

    # Stage 1: Populate DB
    if not args.skip_population:
        populate_db(pool, args.keys_count, args.data_size, args.hash_fields, args.hash_field_size)

    # Stage 2: Perform Reads
    keys = [f"key-{i}" for i in range(args.keys_count)]
    metrics = {"ops": 0, "lock": threading.Lock(), "worker_count": args.connections}

    # Start slow connections
    for i in range(args.slow_connections):
        thread = threading.Thread(target=slow_reader, args=(i, args.host, args.port, args.recv_chunk_size, args.recv_sleep_time))
        thread.daemon = True
        thread.start()

    read_db(pool, keys, metrics)

if __name__ == "__main__":
    main()
