import redis
import threading
import time
import argparse
from typing import List
import signal
import sys
from dataclasses import dataclass
import random
import logging
import socket
from redis.exceptions import ConnectionError, TimeoutError, RedisError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)

@dataclass
class ConnectionStats:
    bytes_read: int = 0
    messages_received: int = 0
    reconnection_attempts: int = 0

class SlowReader:
    def __init__(self, host: str, port: int, channel: str, 
                 min_bytes_recv: int, max_bytes_recv: int,
                 min_recv_sleep_time: float, max_recv_sleep_time: float):
        self.host = host
        self.port = port
        self.channel = channel
        self.min_bytes_recv = min_bytes_recv
        self.max_bytes_recv = max_bytes_recv
        self.min_recv_sleep_time = min_recv_sleep_time
        self.max_recv_sleep_time = max_recv_sleep_time
        self.stats = ConnectionStats()
        self.running = True
        self.reconnect_delay = 1
        self.max_reconnect_delay = 30
        self.connect()

    def connect(self):
        """Establish connection to Redis and subscribe to channel"""
        try:
            self.redis_client = redis.Redis(
                host=self.host, 
                port=self.port,
                socket_keepalive=True,
                socket_keepalive_options={
                    socket.TCP_KEEPIDLE: 30,
                    socket.TCP_KEEPINTVL: 5,
                    socket.TCP_KEEPCNT: 3
                }
            )
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.channel)
            self.reconnect_delay = 1
            logging.info(f"Successfully connected to Redis and subscribed to {self.channel}")
            return True
        except RedisError as e:
            logging.error(f"Failed to connect to Redis: {str(e)}")
            return False

    def reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        self.stats.reconnection_attempts += 1
        logging.warning(f"Attempting to reconnect (attempt {self.stats.reconnection_attempts})")
        
        while self.running:
            try:
                # Close existing connections if any
                try:
                    self.pubsub.close()
                    self.redis_client.close()
                except:
                    pass

                # Attempt to reconnect
                if self.connect():
                    return True
                
            except Exception as e:
                logging.error(f"Reconnection attempt failed: {str(e)}")
            
            # Wait before next attempt with exponential backoff
            logging.info(f"Waiting {self.reconnect_delay} seconds before next reconnection attempt")
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        return False
        
    def get_random_bytes_limit(self) -> int:
        """Get random byte limit for current reading cycle"""
        return random.randint(self.min_bytes_recv, self.max_bytes_recv)
        
    def get_random_sleep_time(self) -> float:
        """Get random sleep time between readings"""
        return random.uniform(self.min_recv_sleep_time, self.max_recv_sleep_time)

    def read_loop(self):
        last_read_time = time.time()
        bytes_read_in_current_second = 0
        current_byte_limit = self.get_random_bytes_limit()
        
        while self.running:
            try:
                current_time = time.time()
                if current_time - last_read_time >= 1:
                    bytes_read_in_current_second = 0
                    last_read_time = current_time
                    current_byte_limit = self.get_random_bytes_limit()
                    logging.debug(f"New byte limit: {current_byte_limit}")
                    
                if bytes_read_in_current_second < current_byte_limit:
                    message = self.pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        data_size = len(str(message['data']))
                        bytes_read_in_current_second += data_size
                        self.stats.bytes_read += data_size
                        self.stats.messages_received += 1
                        logging.debug(f"Received message of size {data_size}")
                else:
                    sleep_time = self.get_random_sleep_time()
                    logging.debug(f"Sleeping for {sleep_time} seconds")
                    time.sleep(sleep_time)

            except (ConnectionError, TimeoutError) as e:
                if self.running:
                    logging.error(f"Connection lost: {str(e)}")
                    if not self.reconnect():
                        logging.error("Failed to reconnect, stopping reader")
                        break
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                if self.running:
                    time.sleep(1)

    def stop(self):
        self.running = False
        try:
            self.pubsub.unsubscribe()
            self.pubsub.close()
            self.redis_client.close()
        except:
            pass

class Publisher:
    def __init__(self, host: str, port: int, channel: str, min_message_size: int, max_message_size: int):
        self.redis_client = redis.Redis(host=host, port=port)
        self.channel = channel
        self.min_message_size = min_message_size
        self.max_message_size = max_message_size
        self.running = True
        self.messages_sent = 0
        self.total_bytes_sent = 0
        
    def generate_message(self) -> str:
        message_size = random.randint(self.min_message_size, self.max_message_size)
        return 'x' * message_size
        
    def publish_loop(self):
        logging.info("Publisher started")
        while self.running:
            try:
                message = self.generate_message()
                self.redis_client.publish(self.channel, message)
                self.messages_sent += 1
                self.total_bytes_sent += len(message)
                time.sleep(0.1)  # Prevent flooding
            except Exception as e:
                logging.error(f"Publisher error: {str(e)}")
                time.sleep(1)
            
    def stop(self):
        self.running = False
        self.redis_client.close()
        logging.info("Publisher stopped")

class BufferTester:
    def __init__(self, host: str, port: int, num_connections: int, 
                 min_bytes_recv: int, max_bytes_recv: int,
                 min_recv_sleep_time: float, max_recv_sleep_time: float,
                 min_message_size: int, max_message_size: int):
        self.channel = "test_channel"
        self.slow_readers: List[SlowReader] = []
        self.reader_threads: List[threading.Thread] = []
        
        # Create slow readers
        for i in range(num_connections):
            reader = SlowReader(
                host=host,
                port=port,
                channel=self.channel,
                min_bytes_recv=min_bytes_recv,
                max_bytes_recv=max_bytes_recv,
                min_recv_sleep_time=min_recv_sleep_time,
                max_recv_sleep_time=max_recv_sleep_time
            )
            self.slow_readers.append(reader)
            thread = threading.Thread(
                target=reader.read_loop,
                name=f"SlowReader-{i+1}"
            )
            self.reader_threads.append(thread)
            
        # Create publisher
        self.publisher = Publisher(host, port, self.channel, min_message_size, max_message_size)
        self.publisher_thread = threading.Thread(
            target=self.publisher.publish_loop,
            name="Publisher"
        )

    def start(self):
        logging.info("Starting test...")
        # Start readers
        for thread in self.reader_threads:
            thread.start()
            
        # Start publisher
        self.publisher_thread.start()
        logging.info("All threads started")
        
    def stop(self):
        logging.info("Stopping test...")
        # Stop publisher first
        self.publisher.stop()
        self.publisher_thread.join()
        
        # Then stop readers
        for reader in self.slow_readers:
            reader.stop()
        for thread in self.reader_threads:
            thread.join()
        logging.info("All threads stopped")
            
    def print_stats(self):
        total_bytes_read = sum(reader.stats.bytes_read for reader in self.slow_readers)
        total_messages_received = sum(reader.stats.messages_received for reader in self.slow_readers)
        total_reconnections = sum(reader.stats.reconnection_attempts for reader in self.slow_readers)
        
        print("\nTest Statistics:")
        print(f"Total messages sent by publisher: {self.publisher.messages_sent}")
        print(f"Total bytes sent by publisher: {self.publisher.total_bytes_sent}")
        if self.publisher.messages_sent > 0:
            print(f"Average message size: {self.publisher.total_bytes_sent / self.publisher.messages_sent:.2f} bytes")
        print(f"Total messages received by all readers: {total_messages_received}")
        print(f"Total bytes read by all readers: {total_bytes_read}")
        print(f"Total reconnection attempts: {total_reconnections}")
        print("\nPer Connection Statistics:")
        for i, reader in enumerate(self.slow_readers):
            print(f"Connection {i + 1}:")
            print(f"  Messages received: {reader.stats.messages_received}")
            print(f"  Bytes read: {reader.stats.bytes_read}")
            print(f"  Reconnection attempts: {reader.stats.reconnection_attempts}")

def main():
    parser = argparse.ArgumentParser(description='Redis Buffer Tester')
    parser.add_argument('--host', default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--connections', type=int, default=5, help='Number of slow connections')
    
    # New receive rate parameters
    parser.add_argument('--min-bytes-recv', type=int, default=500,
                        help='Minimum bytes to receive per second per connection')
    parser.add_argument('--max-bytes-recv', type=int, default=1500,
                        help='Maximum bytes to receive per second per connection')
    parser.add_argument('--min-recv-sleep-time', type=float, default=0.1,
                        help='Minimum sleep time between reads in seconds')
    parser.add_argument('--max-recv-sleep-time', type=float, default=0.5,
                        help='Maximum sleep time between reads in seconds')
    
    # Message size parameters
    parser.add_argument('--min-message-size', type=int, default=100,
                        help='Minimum size of published messages in bytes')
    parser.add_argument('--max-message-size', type=int, default=1000,
                        help='Maximum size of published messages in bytes')
    parser.add_argument('--duration', type=int, default=60,
                        help='Test duration in seconds')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min_message_size > args.max_message_size:
        print("Error: min-message-size cannot be greater than max-message-size")
        sys.exit(1)
    
    if args.min_bytes_recv > args.max_bytes_recv:
        print("Error: min-bytes-recv cannot be greater than max-bytes-recv")
        sys.exit(1)
        
    if args.min_recv_sleep_time > args.max_recv_sleep_time:
        print("Error: min-recv-sleep-time cannot be greater than max-recv-sleep-time")
        sys.exit(1)

    # Test Redis connection before starting
    try:
        redis_client = redis.Redis(host=args.host, port=args.port)
        redis_client.ping()
        redis_client.close()
    except RedisError as e:
        print(f"Error: Could not connect to Redis at {args.host}:{args.port}")
        print(f"Error details: {str(e)}")
        sys.exit(1)
    
    tester = BufferTester(
        host=args.host,
        port=args.port,
        num_connections=args.connections,
        min_bytes_recv=args.min_bytes_recv,
        max_bytes_recv=args.max_bytes_recv,
        min_recv_sleep_time=args.min_recv_sleep_time,
        max_recv_sleep_time=args.max_recv_sleep_time,
        min_message_size=args.min_message_size,
        max_message_size=args.max_message_size
    )
    
    def signal_handler(signum, frame):
        print("\nStopping test...")
        tester.stop()
        tester.print_stats()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"Starting test with:")
    print(f"- {args.connections} connections")
    print(f"- Receive rate: {args.min_bytes_recv} - {args.max_bytes_recv} bytes/second per connection")
    print(f"- Receive sleep time: {args.min_recv_sleep_time} - {args.max_recv_sleep_time} seconds")
    print(f"- Message size range: {args.min_message_size} - {args.max_message_size} bytes")
    print(f"- {args.duration} seconds duration")
    print("\nPress Ctrl+C to stop the test early...")
    
    tester.start()
    time.sleep(args.duration)
    tester.stop()
    tester.print_stats()

if __name__ == "__main__":
    main()
