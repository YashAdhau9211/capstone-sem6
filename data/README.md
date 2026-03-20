# Mock Manufacturing Data

This directory contains generated mock data for testing the Causal AI Manufacturing Platform.

## Quick Start

### Generate Data

```bash
# Generate 6 months of data (default)
python scripts/generate_mock_data.py

# Generate 30 days of data
python scripts/generate_mock_data.py --days 30

# Generate with custom frequency
python scripts/generate_mock_data.py --days 90 --freq 30s
```

### Run Example

```bash
# Test with mock data
python examples/test_with_mock_data.py
```

## Generated Files

After running the generator, you'll find:

```
data/mock/
├── furnace-01_data.csv          # Blast Furnace data (22 variables)
├── mill-01_data.csv             # Rolling Mill data (21 variables)
├── anneal-01_data.csv           # Annealing Furnace data (22 variables)
├── all_stations_data.csv        # Combined data from all stations
└── metadata.json                # Ground truth causal relationships
```

## Data Structure

Each CSV file contains:
- `timestamp` - ISO 8601 timestamp
- `station_id` - Station identifier (furnace-01, mill-01, anneal-01)
- 20+ process variables with realistic values and embedded causal relationships

## Ground Truth Causal Relationships

### Blast Furnace (furnace-01)
1. `hot_blast_temp` → `furnace_top_temp` → `pig_iron_production_rate`
2. `oxygen_flow` → `carbon_content` → `iron_quality_index`
3. `coal_injection_rate` → `fuel_consumption` → `power_consumption`
4. `ore_feed_rate` → `slag_volume`

### Rolling Mill (mill-01)
1. `slab_entry_temp` → `rolling_force` → `thickness_exit`
2. `roll_speed` → `surface_quality_index`
3. `cooling_water_flow` → `slab_exit_temp` → `flatness`
4. `motor_power` → `vibration_x`, `vibration_y`

### Annealing Furnace (anneal-01)
1. `heating_zone_temp` → `soaking_zone_temp` → `grain_size` → `hardness`
2. `strip_speed` → `cooling_rate` → `tensile_strength`
3. `hydrogen_concentration` → `surface_quality`
4. `gas_consumption` → `electricity_consumption`

## Usage Examples

### Load Data

```python
import pandas as pd

# Load single station
data = pd.read_csv('data/mock/furnace-01_data.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])

# Load all stations
all_data = pd.read_csv('data/mock/all_stations_data.csv')
```

### Test Causal Discovery

```python
# Prepare data for causal discovery
data = pd.read_csv('data/mock/furnace-01_data.csv')
data = data.drop(columns=['timestamp', 'station_id'])

# Run DirectLiNGAM
from src.causal_engine import CausalDiscoveryEngine
engine = CausalDiscoveryEngine()
dag = engine.discover_linear(data)

# Compare with ground truth in metadata.json
```

### Validate Data Quality

```python
from src.data_integration.data_validator import DataValidator

data = pd.read_csv('data/mock/furnace-01_data.csv')
validator = DataValidator()

# Check ranges
violations = validator.check_range(data, 'hot_blast_temp', (1000, 1200))
print(f"Range violations: {len(violations)}")

# Check completeness
completeness = validator.calculate_completeness(data, window=pd.Timedelta('24h'))
print(f"Data completeness: {completeness}")
```

## Documentation

- **Setup Guide**: `docs/MOCK_ISA95_SETUP.md`
- **Usage Guide**: `docs/MOCK_DATA_USAGE_GUIDE.md`
- **Generator Script**: `scripts/generate_mock_data.py`
- **Example Code**: `examples/test_with_mock_data.py`

## Data Characteristics

- **Frequency**: 1-minute intervals (configurable)
- **Duration**: 180 days (configurable)
- **Noise Level**: 2-3% Gaussian noise
- **Anomalies**: 3-5% of data points
- **Patterns**: Daily cycles, shift changes, realistic sensor behavior

## Notes

- This is **synthetic data** for testing only
- Ground truth causal relationships are embedded in the generation process
- Use this data to validate causal discovery algorithms
- Real ISA-95 systems will have different characteristics
