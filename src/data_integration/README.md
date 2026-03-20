# ISA-95 Connector Framework

This module implements the data integration layer for connecting to ISA-95 compliant industrial control systems across all automation levels (ERP, MES, SCADA, PLC, IIoT sensors).

## Components

### Base Connector (`isa95_connector.py`)

The `ISA95Connector` abstract base class provides:

- **Connection Pooling**: Configurable pool size (default: 10 connections)
- **Exponential Backoff Retry**: 1s, 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s max
- **Connection Status Caching**: 100ms TTL for fast status queries
- **Abstract Methods**: `connect()`, `disconnect()`, `get_connection_status()`, `read_data()`, `subscribe_realtime()`

### OPC UA Connector (`opcua_connector.py`)

Connects to SCADA and PLC systems using the `asyncua` library:

- OPC UA client implementation with authentication
- Variable subscription for real-time data streaming
- 30-second heartbeat keepalive mechanism
- Historical data access support

### Database Connectors (`database_connector.py`)

Connects to ERP and MES systems using SQLAlchemy:

- **DatabaseConnector**: Base class for SQL database connectivity
- **ODBCConnector**: ODBC-based connections (via pyodbc)
- **JDBCConnector**: JDBC-based connections (placeholder for JayDeBeApi)
- Query execution for historical data retrieval
- Connection validation and health checks (60-second interval)
- Polling-based real-time subscription

### MQTT Connector (`mqtt_connector.py`)

Connects to IIoT sensor networks using `paho-mqtt`:

- MQTT client with QoS configuration (0, 1, or 2)
- Topic subscription with wildcard support (+, #)
- Message buffering (configurable size, default: 10,000 messages)
- JSON payload parsing with automatic timestamp extraction
- TLS/SSL support for secure connections

### Monitoring (`monitoring.py`)

Connection failure logging and monitoring system:

- **ConnectionMonitor**: Centralized monitoring for all connectors
- Event logging with severity levels (INFO, WARNING, ERROR, CRITICAL)
- Health status tracking with uptime percentage calculation
- Event history with filtering capabilities
- Graceful degradation support for partial connectivity
- Periodic health checks (configurable interval)

## Usage Examples

### OPC UA Connection

```python
from src.data_integration import OPCUAConnector, SystemConfig

config = SystemConfig(
    system_id="scada_01",
    system_type="SCADA",
    host="192.168.1.100",
    port=4840,
    username="admin",
    password="password",
    pool_size=10
)

connector = OPCUAConnector(config)
await connector.connect()

# Read historical data
time_range = TimeRange(start=datetime.now() - timedelta(hours=1), end=datetime.now())
df = await connector.read_data(["ns=2;s=Temperature", "ns=2;s=Pressure"], time_range)

# Subscribe to real-time updates
async def callback(data: pd.DataFrame):
    print(f"Received data: {data}")

subscription = await connector.subscribe_realtime(["ns=2;s=Temperature"], callback)
```

### Database Connection

```python
from src.data_integration import DatabaseConnector, SystemConfig

config = SystemConfig(
    system_id="mes_01",
    system_type="MES",
    host="db.example.com",
    port=5432,
    username="mes_user",
    password="password",
    connection_params={
        "db_type": "postgresql",
        "database": "manufacturing",
        "table_name": "sensor_data",
        "timestamp_column": "timestamp",
        "variable_column": "sensor_id",
        "value_column": "value",
        "quality_column": "quality"
    }
)

connector = DatabaseConnector(config)
await connector.connect()

# Read historical data
df = await connector.read_data(["temp_sensor_01", "pressure_sensor_02"], time_range)
```

### MQTT Connection

```python
from src.data_integration import MQTTConnector, SystemConfig

config = SystemConfig(
    system_id="iiot_01",
    system_type="IIoT",
    host="mqtt.example.com",
    port=1883,
    username="mqtt_user",
    password="password",
    connection_params={
        "qos": 1,
        "buffer_size": 10000,
        "client_id": "manufacturing_platform"
    }
)

connector = MQTTConnector(config)
await connector.connect()

# Subscribe to topics (supports wildcards)
subscription = await connector.subscribe_realtime(
    ["factory/line1/+/temperature", "factory/line2/#"],
    callback
)
```

### Monitoring

```python
from src.data_integration import get_monitor

monitor = get_monitor()

# Register connectors
monitor.register_connector(opcua_connector)
monitor.register_connector(db_connector)
monitor.register_connector(mqtt_connector)

# Start periodic monitoring
monitor.start_monitoring(interval=60)

# Get health status
health = monitor.get_system_health("scada_01")
print(f"System: {health.system_id}")
print(f"Healthy: {health.is_healthy}")
print(f"Uptime: {health.uptime_percentage:.2f}%")
print(f"Total Failures: {health.total_failures}")

# Get event history
events = monitor.get_event_history(system_id="scada_01", limit=10)
for event in events:
    print(f"{event.timestamp}: {event.event_type.value} - {event.error_details}")
```

## Requirements Mapping

### Task 3.1: ISA95Connector Base Class ✓
- ✓ Abstract methods: `connect()`, `disconnect()`, `get_connection_status()`, `read_data()`, `subscribe_realtime()`
- ✓ Connection pooling with configurable pool size (default: 10)
- ✓ Exponential backoff retry logic: 1s, 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s max
- ✓ Connection status caching with 100ms TTL
- Requirements: 1.1, 1.2, 1.3, 1.4, 1.7, 1.8

### Task 3.2: OPC UA Connector ✓
- ✓ `asyncua` library for OPC UA client implementation
- ✓ Connection to OPC UA servers with authentication
- ✓ Variable subscription for real-time data streaming
- ✓ 30-second heartbeat keepalive mechanism
- Requirements: 1.3, 1.4

### Task 3.3: ODBC/JDBC Connectors ✓
- ✓ `sqlalchemy` for database connectivity
- ✓ Query execution for historical data retrieval
- ✓ Connection validation and health checks
- Requirements: 1.1, 1.2

### Task 3.4: MQTT Connector ✓
- ✓ `paho-mqtt` library for MQTT client
- ✓ Topic subscription and message parsing
- ✓ QoS configuration and message buffering
- Requirements: 1.4

### Task 3.5: Connection Failure Logging and Monitoring ✓
- ✓ Log connection failures with timestamp, system ID, error details
- ✓ Emit connection status events to monitoring system
- ✓ Implement graceful degradation for partial connectivity
- Requirements: 1.5, 1.6

## Testing

All components have been tested with unit tests in `tests/test_isa95_connector.py`:

- Connection lifecycle (connect, disconnect, reconnect)
- Connection status caching
- Data reading and real-time subscription
- Connection pooling
- Exponential backoff retry
- Error handling

Run tests with:
```bash
pytest tests/test_isa95_connector.py -v
```

## Dependencies

- `asyncua>=1.0.0` - OPC UA client
- `sqlalchemy>=2.0.0` - Database connectivity
- `pyodbc>=5.0.0` - ODBC driver
- `paho-mqtt>=1.6.1` - MQTT client
- `pandas>=2.1.0` - Data manipulation
