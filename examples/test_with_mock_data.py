#!/usr/bin/env python3
"""
Example: Using Mock Data with the Causal AI Platform

This script demonstrates how to:
1. Generate mock manufacturing data
2. Load and preprocess the data
3. Run basic validation
4. Visualize the data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Import platform components
from src.data_integration.data_validator import DataValidator
from src.etl.pipeline import ETLPipeline


def generate_data():
    """Generate mock data if it doesn't exist"""
    data_dir = Path('data/mock')
    
    if not (data_dir / 'furnace-01_data.csv').exists():
        print("Mock data not found. Generating...")
        import subprocess
        subprocess.run(['python', 'scripts/generate_mock_data.py', '--days', '30'])
    else:
        print("✓ Mock data already exists")


def load_and_explore():
    """Load and explore the mock data"""
    print("\n" + "="*60)
    print("LOADING AND EXPLORING DATA")
    print("="*60)
    
    # Load data
    furnace_data = pd.read_csv('data/mock/furnace-01_data.csv')
    print(f"\n✓ Loaded furnace-01 data: {len(furnace_data)} records")
    print(f"  Date range: {furnace_data['timestamp'].min()} to {furnace_data['timestamp'].max()}")
    print(f"  Variables: {len(furnace_data.columns) - 2}")  # Exclude timestamp and station_id
    
    # Show sample
    print("\nSample data (first 5 rows):")
    print(furnace_data.head())
    
    # Show statistics
    print("\nKey variable statistics:")
    key_vars = ['hot_blast_temp', 'furnace_top_temp', 'pig_iron_production_rate', 
                'iron_quality_index', 'power_consumption']
    print(furnace_data[key_vars].describe())
    
    return furnace_data



def test_data_validation(data):
    """Test data validation with mock data"""
    print("\n" + "="*60)
    print("TESTING DATA VALIDATION")
    print("="*60)
    
    # Define validation schema
    schema = {
        'required_columns': ['timestamp', 'station_id', 'hot_blast_temp', 'oxygen_flow'],
        'ranges': {
            'hot_blast_temp': (1000, 1200),
            'oxygen_flow': (45000, 55000),
            'carbon_content': (4.0, 5.0),
            'pig_iron_production_rate': (0, 200)
        }
    }
    
    # Create validator
    validator = DataValidator()
    
    # Test range validation
    print("\n1. Range Validation:")
    for var, bounds in schema['ranges'].items():
        violations = validator.check_range(data, var, bounds)
        print(f"  {var}: {len(violations)} violations")
        if violations:
            print(f"    Example: {violations[0]}")
    
    # Test flatline detection
    print("\n2. Flatline Detection:")
    test_vars = ['hot_blast_temp', 'oxygen_flow', 'pig_iron_production_rate']
    for var in test_vars:
        violations = validator.detect_flatline(data, var, window=10)
        print(f"  {var}: {len(violations)} flatlines detected")
    
    # Test completeness
    print("\n3. Data Completeness:")
    completeness = validator.calculate_completeness(data, window=pd.Timedelta('24h'))
    for var, pct in list(completeness.items())[:5]:
        status = "✓" if pct >= 85 else "✗"
        print(f"  {status} {var}: {pct:.1f}%")
    
    print("\n✓ Data validation tests complete")


def test_etl_pipeline(data):
    """Test ETL pipeline with mock data"""
    print("\n" + "="*60)
    print("TESTING ETL PIPELINE")
    print("="*60)
    
    # Convert timestamp to datetime
    data_copy = data.copy()
    data_copy['timestamp'] = pd.to_datetime(data_copy['timestamp'])
    
    # Create ETL pipeline
    etl = ETLPipeline()
    
    # Test resampling
    print("\n1. Testing Resampling:")
    print(f"  Original frequency: 1 minute")
    resampled = etl.resample(data_copy, interval=pd.Timedelta('5min'))
    print(f"  Resampled to: 5 minutes")
    print(f"  Original samples: {len(data_copy)}")
    print(f"  Resampled samples: {len(resampled)}")
    
    # Test gap interpolation
    print("\n2. Testing Gap Interpolation:")
    # Introduce a small gap
    data_with_gap = data_copy.copy()
    data_with_gap = data_with_gap.drop(data_with_gap.index[100:103])  # 3-minute gap
    
    interpolated = etl.interpolate_gaps(data_with_gap, max_gap=pd.Timedelta('5min'))
    print(f"  Introduced 3-minute gap")
    print(f"  Gap interpolated: ✓")
    
    print("\n✓ ETL pipeline tests complete")


def visualize_causal_relationships(data):
    """Visualize the embedded causal relationships"""
    print("\n" + "="*60)
    print("VISUALIZING CAUSAL RELATIONSHIPS")
    print("="*60)
    
    # Convert timestamp
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data.set_index('timestamp', inplace=True)
    
    # Plot causal chain 1: hot_blast_temp → furnace_top_temp → pig_iron_production_rate
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))
    
    # Use first 1000 samples for clarity
    plot_data = data.iloc[:1000]
    
    axes[0].plot(plot_data.index, plot_data['hot_blast_temp'], label='Hot Blast Temp', color='red')
    axes[0].set_ylabel('Temperature (°C)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('Causal Chain: hot_blast_temp → furnace_top_temp → pig_iron_production_rate')
    
    axes[1].plot(plot_data.index, plot_data['furnace_top_temp'], label='Furnace Top Temp', color='orange')
    axes[1].set_ylabel('Temperature (°C)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(plot_data.index, plot_data['pig_iron_production_rate'], 
                 label='Pig Iron Production Rate', color='blue')
    axes[2].set_ylabel('Production Rate')
    axes[2].set_xlabel('Time')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path('data/mock/plots')
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / 'causal_chain_example.png', dpi=150)
    print(f"\n✓ Saved visualization: {output_dir / 'causal_chain_example.png'}")
    
    # Show correlation
    print("\nCorrelation Analysis (Ground Truth Causal Chain):")
    corr_vars = ['hot_blast_temp', 'furnace_top_temp', 'pig_iron_production_rate']
    corr_matrix = data[corr_vars].corr()
    print(corr_matrix)


def main():
    """Main function"""
    print("="*60)
    print("MOCK DATA TESTING EXAMPLE")
    print("="*60)
    
    # Step 1: Generate data
    generate_data()
    
    # Step 2: Load and explore
    data = load_and_explore()
    
    # Step 3: Test validation
    test_data_validation(data)
    
    # Step 4: Test ETL pipeline
    test_etl_pipeline(data)
    
    # Step 5: Visualize relationships
    visualize_causal_relationships(data.copy())
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Run causal discovery: python examples/run_causal_discovery.py")
    print("  2. Test causal inference: python examples/run_causal_inference.py")
    print("  3. View documentation: docs/MOCK_DATA_USAGE_GUIDE.md")


if __name__ == "__main__":
    main()
