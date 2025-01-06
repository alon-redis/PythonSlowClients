import redis
import socket
import argparse
import time
import threading
from tqdm import tqdm

# Conversion factor for MB to bytes
MB_TO_BYTES = 1048576

def populate_data(redis_host, redis_port, num_connections, initial_key_size, delta):
    pool = redis.ConnectionPool(host=redis_host, port=redis_port, max_connections=num_connections)
    client = redis.Redis(connection_pool=pool)

    try:
        for i in range(1, num_connections + 1):
            key = f"key_{i}"
            value_size = (initial_key_size + (i - 1) * delta) * MB_TO_BYTES
            value = "x" * value_size
            client.set(key, value)
            print(f"Set key: {key} with size: {value_size} bytes")
    finally:
        pool.disconnect()
        print("All connections closed after populating data.")

def fetch_data_slowly(redis_host, redis_port, num_connections, sleep_time):
    def handle_connection(index):
        try:
            with socket.create_connection((redis_host, redis_port)) as s:
                key = f"key_{index}\r\n"
                command = f"GET {key}".encode('utf-8')
                s.sendall(command)

                # Use tqdm to show the sleep progress
                for _ in tqdm(range(int(sleep_time * 10)), desc=f"Sleeping for key_{index}", leave=False):
                    time.sleep(0.1)

                print(f"Sent GET command for: {key.strip()} but reading response very slowly or not at all.")
        except Exception as e:
            print(f"Error with connection {index}: {e}")

    threads = []
    for i in range(1, num_connections + 1):
        thread = threading.Thread(target=handle_connection, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate and fetch data from Redis using sockets.")
    parser.add_argument("--redis_host", type=str, required=True, help="Redis server hostname.")
    parser.add_argument("--redis_port", type=int, required=True, help="Redis server port.")
    parser.add_argument("--num_connections", type=int, required=True, help="Number of connections to use.")
    parser.add_argument("--initial_key_size", type=int, required=True, help="Initial key size in MB.")
    parser.add_argument("--delta", type=int, required=True, help="Delta to increase key size in MB.")
    parser.add_argument("--sleep_time", type=float, required=True, help="Time to sleep between sending commands in the fetch stage.")
    parser.add_argument("--noflush", action="store_true", help="Do not flush the Redis database before starting.")

    args = parser.parse_args()

    if not args.noflush:
        client = redis.Redis(host=args.redis_host, port=args.redis_port)
        client.flushall()
        print("Flushed all Redis databases.")

    print("Starting population stage...")
    populate_data(args.redis_host, args.redis_port, args.num_connections, args.initial_key_size, args.delta)

    print("Starting fetch stage...")
    fetch_data_slowly(args.redis_host, args.redis_port, args.num_connections, args.sleep_time)
