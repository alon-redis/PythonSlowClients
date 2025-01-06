# Redis Concurrent Slow Connections Tester

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
pip3 install redis tqdm
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
| `--recv_chunk_size_min` | Minimum chunk size for socket `recv` in bytes.                 | 32          |
| `--recv_chunk_size_max` | Maximum chunk size for socket `recv` in bytes.                 | 128         |
| `--recv_sleep_time`   | Sleep time between socket `recv` operations in seconds.        | 1.0         |
| `--hash_fields`       | Number of fields in the large hash.                            | 1000000     |
| `--hash_field_size`   | Size of each field value in the large hash in bytes.           | 100         |

### Example

Populate the database and test with 10 normal connections and 2 slow connections:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --slow_connections 2
```

Skip the population stage:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --slow_connections 2 --skip_population
```

Control slow connection parameters (chunk size range and sleep time):
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --slow_connections 2 --recv_chunk_size_min 64 --recv_chunk_size_max 256 --recv_sleep_time 0.5
```

Control large hash size:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --keys_count 1000 --connections 10 --hash_fields 500000 --hash_field_size 200
```

Best practise for controlling the tool:
```bash
python parallel_redis_connections.py --host 127.0.0.1 --port 6379 --connections 100 --keys_count 1000 --data_size 1024 --hash_fields 50000 --hash_field_size 1024 --slow_connections 10 --skip_population --recv_chunk_size_min 2048 --recv_chunk_size_max 8192 --recv_sleep_time 0.01
```

## Functionality

### 1. **Population Stage**
- Populates Redis with the specified number of keys.
- Creates a large hash (`large-hash`) with a configurable number of fields and field sizes.

### 2. **Slow Connections**
- Simulates slow connections using raw sockets.
- Performs `HGETALL` on the large hash and processes the response in small chunks with a configurable delay.

### 3. **Read Operations**
- Multiple threads perform `GET` operations on the populated keys.
- Measures throughput

## Output

- **Throughput**: Operations per second.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.






******************************************************************************************************************************************************************************************************
******************************************************************************************************************************************************************************************************

# differentBufferSize.py

## Overview
`differentBufferSize.py` is a Python script that interacts with a Redis server using both connection pools and sockets. It has two main stages: data population and data fetching.

- **Population Stage:** Uses a Redis connection pool to populate the database with keys of varying sizes.
- **Fetch Stage:** Opens parallel socket connections to fetch data from Redis. The fetch process simulates slow reading using delays, with a progress bar displayed via the `tqdm` package.

## Usage
```bash
python differentBufferSize.py --redis_host <hostname> \
                             --redis_port <port> \
                             --num_connections <connections> \
                             --initial_key_size <size_in_MB> \
                             --delta <size_in_MB> \
                             --sleep_time <seconds> \
                             [--noflush]
```

### Parameters:
- `--redis_host`: Redis server hostname.
- `--redis_port`: Redis server port.
- `--num_connections`: Number of parallel connections to use.
- `--initial_key_size`: Initial key size in megabytes.
- `--delta`: Incremental increase in key size per connection in megabytes.
- `--sleep_time`: Time to sleep (in seconds) between sending commands during the fetch stage.
- `--noflush`: Prevents flushing the Redis database before starting.

## Dependencies
- `redis`
- `socket`
- `argparse`
- `tqdm`

## Example
```bash
python3 differentBufferSize.py --redis_host redis-10000.alon-5160.env0.qa.redis.com --redis_port 10000 --num_connections 20 --sleep_time 60 --initial_key_size 10 --delta 5
```



