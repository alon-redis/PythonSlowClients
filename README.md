# Redis Parallel Connections Tester

This repository contains a Python script to test parallel connections to a Redis server. The script includes functionalities to simulate normal and slow connections, populate the database, and measure performance metrics such as throughput and latency.

## Features

1. **Parallel Connections**: Test Redis with multiple concurrent connections.
2. **Slow Connections**: Simulate slow clients using raw sockets.
3. **Database Population**: Populate Redis with keys and a large hash.
4. **Performance Metrics**: Measure throughput and latency.
5. **Configurable Parameters**: Customize test parameters through command-line arguments.

## Prerequisites

- Python 3.8 or above
- `redis` Python library

Install the required dependencies:
```bash
pip install redis
```

## Usage

### Command-Line Arguments

| Argument              | Description                                                      | Default     |
|-----------------------|------------------------------------------------------------------|-------------|
| `--host`              | Redis host address (required).                                  | N/A         |
| `--port`              | Redis port number (required).                                   | N/A         |
| `--data_size`         | Size of data in bytes for key population.                      | 1024        |
| `--connections`       | Number of parallel connections.                                | 10          |
| `--slow_connections`  | Number of slow connections.                                     | 0           |
| `--keys_count`        | Number of keys to populate during the first stage (required).  | N/A         |
| `--skip_population`   | Skip the population stage.                                      | False       |
| `--recv_chunk_size`   | Chunk size for socket `recv` in bytes.                         | 64          |
| `--recv_sleep_time`   | Sleep time between socket `recv` operations in seconds.        | 1.0         |

### Example

Populate the database and test with 10 normal connections and 2 slow connections:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --slow_connections 2
```

Skip the population stage:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --slow_connections 2 --skip_population
```

## Functionality

### 1. **Population Stage**
- Populates Redis with the specified number of keys.
- Creates a large hash (`large-hash`) with 1 million fields and a total size of ~10MB.

### 2. **Slow Connections**
- Simulates slow connections using raw sockets.
- Performs `HGETALL` on the large hash and processes the response in small chunks with a configurable delay.

### 3. **Read Operations**
- Multiple threads perform `GET` operations on the populated keys.
- Measures throughput and latency.

## Output

- **Throughput**: Operations per second.
- **Average Latency**: Average time taken per operation.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.

