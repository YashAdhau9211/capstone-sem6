# Quick Start: Using Mock Data

## 🚀 Generate Mock Data (3 Easy Ways)

### Option 1: Using Make (Easiest)
```bash
make mock-data
```

### Option 2: Using Python Script
```bash
# Generate 30 days of data
python scripts/generate_mock_data.py --days 30

# Generate 6 months of data (default)
python scripts/generate_mock_data.py

# Custom configuration
python scripts/generate_mock_data.py --start-date 2024-01-01 --days 90 --freq 1min
```

### Option 3: Using Python Code
```python
from scripts.generate_mock_data import ManufacturingDataGenerator

generator = ManufacturingDataGenerator(
    start_date='2024-01-01',
    days=30,
    freq='1min'
)
stations = generator.generate_all_stations(output_dir='data/mock')
```

## 📁 What Gets Generated

```
data/mock/
├── furnace-01_data.csv          # Blast Furnace (22 variables)
├── mill-01_data.csv             # Rolling Mill (21 variables)
├── anneal-01_data.csv           # Annealing Furnace (22 variables)
├── all_stations_data.csv        # Combined data
└── metadata.json                # Ground truth causal relationships
```

## 🧪 Test with Mock Data

### Run Example Tests
```bash
make test-mock
# or
python examples/test_with_mock_data.py
```

### Load in Python
```python
import pandas as pd

# Load data
data = pd.read_csv('data/mock/furnace-01_data.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])

# View first few rows
print(data.head())

# Check shape
print(f"Shape: {data.shape}")
print(f"Variables: {data.columns.tolist()}")
```

## 🔍 Use Cases

### 1. Test Data Integration
```python
from src.data_integration.data_validator import DataValidator

data = pd.read_csv('data/mock/furnace-01_data.csv')
validator = DataValidator()

# Validate ranges
violations = validator.check_range(data, 'hot_blast_temp', (1000, 1200))
print(f"Violations: {len(violations)}")
```

### 2. Test ETL Pipeline
```python
from src.etl.pipeline import ETLPipeline

data = pd.read_csv('data/mock/furnace-01_data.csv')
etl = ETLPipeline()

# Resample to 5-minute intervals
resampled = etl.resample(data, interval=pd.Timedelta('5min'))
print(f"Resampled from {len(data)} to {len(resampled)} samples")
```

### 3. Test Causal Discovery
```python
# Load data (drop non-numeric columns)
data = pd.read_csv('data/mock/furnace-01_data.csv')
data = data.drop(columns=['timestamp', 'station_id'])

# Run causal discovery (when implemented)
# from src.causal_engine import CausalDiscoveryEngine
# engine = CausalDiscoveryEngine()
# dag = engine.discover_linear(data)
```

## 📊 Ground Truth Causal Relationships

The data has **embedded causal relationships** for validation:

### Blast Furnace
- `hot_blast_temp` → `furnace_top_temp` → `pig_iron_production_rate`
- `oxygen_flow` → `carbon_content` → `iron_quality_index`
- `coal_injection_rate` → `fuel_consumption` → `power_consumption`

### Rolling Mill
- `slab_entry_temp` → `rolling_force` → `thickness_exit`
- `roll_speed` → `surface_quality_index`
- `cooling_water_flow` → `slab_exit_temp` → `flatness`

### Annealing Furnace
- `heating_zone_temp` → `soaking_zone_temp` → `grain_size` → `hardness`
- `strip_speed` → `cooling_rate` → `tensile_strength`

Check `data/mock/metadata.json` for complete ground truth.

## 📚 Documentation

- **Detailed Setup**: `docs/MOCK_ISA95_SETUP.md`
- **Usage Guide**: `docs/MOCK_DATA_USAGE_GUIDE.md`
- **Data README**: `data/README.md`

## 💡 Tips

1. **Start small**: Generate 7-30 days for quick testing
2. **Verify ground truth**: Compare discovered DAGs with metadata.json
3. **Test incrementally**: Start with data validation, then ETL, then causal discovery
4. **Use examples**: Run `examples/test_with_mock_data.py` to see it in action

## ❓ Common Questions

**Q: How much data should I generate?**
- Testing: 7-30 days
- Development: 30-90 days
- Performance testing: 180 days

**Q: Can I change the sampling frequency?**
- Yes! Use `--freq` parameter: `1min`, `30s`, `5min`, `1h`

**Q: Where are the causal relationships?**
- Embedded in the data generation process
- Ground truth documented in `data/mock/metadata.json`

**Q: Is this real manufacturing data?**
- No, it's synthetic but realistic
- Based on steel manufacturing processes
- Includes realistic noise, patterns, and anomalies

## 🎯 Next Steps

1. Generate data: `make mock-data`
2. Run tests: `make test-mock`
3. Explore data: Open `data/mock/furnace-01_data.csv` in your favorite tool
4. Build features: Use this data to test your implementations
5. Validate: Compare discovered relationships with ground truth

---

**Need help?** Check the documentation in `docs/` or run `make help`
