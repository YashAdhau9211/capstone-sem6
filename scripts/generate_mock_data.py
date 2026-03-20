#!/usr/bin/env python3
"""
Mock Manufacturing Data Generator

Generates realistic time-series data for 3 manufacturing stations
with embedded causal relationships for testing the Causal AI platform.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json


class ManufacturingDataGenerator:
    """Generate realistic manufacturing time-series data with causal relationships"""
    
    def __init__(self, start_date: str, days: int = 180, freq: str = "1min"):
        """
        Args:
            start_date: Start date in YYYY-MM-DD format
            days: Number of days to generate
            freq: Sampling frequency (e.g., '1min', '30s', '1h')
        """
        self.start_date = pd.to_datetime(start_date)
        self.days = days
        self.freq = freq
        self.timestamps = pd.date_range(
            start=self.start_date,
            periods=days * 24 * 60 if freq == "1min" else days * 24,
            freq=freq
        )
        self.n_samples = len(self.timestamps)
        
    def add_noise(self, signal: np.ndarray, noise_level: float = 0.02) -> np.ndarray:
        """Add Gaussian noise to signal"""
        return signal + np.random.normal(0, noise_level * np.abs(signal).mean(), len(signal))

    def add_anomalies(self, signal: np.ndarray, anomaly_rate: float = 0.05) -> np.ndarray:
        """Inject anomalies into signal"""
        anomaly_indices = np.random.choice(
            len(signal), 
            size=int(len(signal) * anomaly_rate), 
            replace=False
        )
        signal_copy = signal.copy()
        signal_copy[anomaly_indices] *= np.random.uniform(1.2, 1.8, len(anomaly_indices))
        return signal_copy
    
    def generate_blast_furnace_data(self) -> pd.DataFrame:
        """Generate data for Blast Furnace station with causal relationships"""
        
        # Root causes (exogenous variables)
        hot_blast_temp = 1100 + 50 * np.sin(2 * np.pi * np.arange(self.n_samples) / (24 * 60)) + \
                         self.add_noise(np.ones(self.n_samples) * 1100, 0.03)
        oxygen_flow = 50000 + 2000 * np.sin(2 * np.pi * np.arange(self.n_samples) / (12 * 60)) + \
                      self.add_noise(np.ones(self.n_samples) * 50000, 0.02)
        coal_injection_rate = 180 + 10 * np.random.randn(self.n_samples)
        ore_feed_rate = 2000 + 50 * np.random.randn(self.n_samples)
        
        # Causal chain 1: hot_blast_temp → furnace_top_temp → pig_iron_production_rate
        furnace_top_temp = 0.8 * hot_blast_temp + 200 + self.add_noise(np.zeros(self.n_samples), 10)
        pig_iron_production_rate = 0.05 * furnace_top_temp + 50 + self.add_noise(np.zeros(self.n_samples), 2)
        
        # Causal chain 2: oxygen_flow → carbon_content → iron_quality_index
        carbon_content = 4.5 - 0.00003 * oxygen_flow + self.add_noise(np.zeros(self.n_samples), 0.1)
        iron_quality_index = 90 - 2 * np.abs(carbon_content - 4.2) + self.add_noise(np.zeros(self.n_samples), 1)

        # Causal chain 3: coal_injection_rate → fuel_consumption → power_consumption
        fuel_consumption = 1.2 * coal_injection_rate + 50 + self.add_noise(np.zeros(self.n_samples), 5)
        power_consumption = 0.8 * fuel_consumption + 1000 + self.add_noise(np.zeros(self.n_samples), 20)
        
        # Causal chain 4: ore_feed_rate → slag_volume
        slag_volume = 0.15 * ore_feed_rate + self.add_noise(np.zeros(self.n_samples), 10)
        
        # Other variables (influenced by multiple factors)
        blast_pressure = 3.5 + 0.0001 * oxygen_flow + self.add_noise(np.zeros(self.n_samples), 0.05)
        top_pressure = 2.0 + 0.0002 * ore_feed_rate + self.add_noise(np.zeros(self.n_samples), 0.03)
        hearth_temp = 1500 + 0.2 * hot_blast_temp + self.add_noise(np.zeros(self.n_samples), 15)
        silicon_content = 0.5 + 0.0001 * furnace_top_temp + self.add_noise(np.zeros(self.n_samples), 0.02)
        sulfur_content = 0.03 + self.add_noise(np.ones(self.n_samples) * 0.03, 0.005)
        iron_temperature = 1450 + 0.3 * furnace_top_temp + self.add_noise(np.zeros(self.n_samples), 10)
        blast_volume = 3000 + 100 * np.random.randn(self.n_samples)
        tuyere_count_active = np.random.randint(28, 33, self.n_samples)
        vibration_level = 2.5 + 0.001 * power_consumption + self.add_noise(np.zeros(self.n_samples), 0.2)
        acoustic_signature = 75 + 0.01 * blast_volume + self.add_noise(np.zeros(self.n_samples), 2)
        
        # Add anomalies to some variables
        pig_iron_production_rate = self.add_anomalies(pig_iron_production_rate, 0.03)
        iron_quality_index = self.add_anomalies(iron_quality_index, 0.02)
        
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'station_id': 'furnace-01',
            'hot_blast_temp': hot_blast_temp,
            'furnace_top_temp': furnace_top_temp,
            'hearth_temp': hearth_temp,
            'blast_pressure': blast_pressure,
            'top_pressure': top_pressure,
            'oxygen_flow': oxygen_flow,
            'coal_injection_rate': coal_injection_rate,
            'ore_feed_rate': ore_feed_rate,
            'carbon_content': carbon_content,
            'silicon_content': silicon_content,
            'sulfur_content': sulfur_content,
            'pig_iron_production_rate': pig_iron_production_rate,
            'slag_volume': slag_volume,
            'power_consumption': power_consumption,
            'fuel_consumption': fuel_consumption,
            'iron_temperature': iron_temperature,
            'iron_quality_index': iron_quality_index,
            'blast_volume': blast_volume,
            'tuyere_count_active': tuyere_count_active,
            'vibration_level': vibration_level,
            'acoustic_signature': acoustic_signature
        })

    def generate_rolling_mill_data(self) -> pd.DataFrame:
        """Generate data for Rolling Mill station"""
        
        # Root causes
        slab_entry_temp = 1200 + 30 * np.sin(2 * np.pi * np.arange(self.n_samples) / (24 * 60)) + \
                          self.add_noise(np.ones(self.n_samples) * 1200, 0.02)
        roll_speed = 5.0 + 0.5 * np.sin(2 * np.pi * np.arange(self.n_samples) / (8 * 60)) + \
                     self.add_noise(np.ones(self.n_samples) * 5.0, 0.05)
        cooling_water_flow = 500 + 20 * np.random.randn(self.n_samples)
        motor_power = 2000 + 100 * np.random.randn(self.n_samples)
        
        # Causal relationships
        rolling_force = 8000 + 5 * (1250 - slab_entry_temp) + self.add_noise(np.zeros(self.n_samples), 100)
        thickness_exit = 10 - 0.0005 * rolling_force + self.add_noise(np.zeros(self.n_samples), 0.1)
        surface_quality_index = 85 + 2 * roll_speed - 0.5 * np.abs(roll_speed - 5.0) + \
                                self.add_noise(np.zeros(self.n_samples), 1)
        slab_exit_temp = slab_entry_temp - 0.5 * cooling_water_flow + self.add_noise(np.zeros(self.n_samples), 10)
        flatness = 0.5 - 0.0001 * np.abs(slab_exit_temp - 1000) + self.add_noise(np.zeros(self.n_samples), 0.05)
        vibration_x = 1.0 + 0.0003 * motor_power + self.add_noise(np.zeros(self.n_samples), 0.1)
        vibration_y = 0.8 + 0.0002 * motor_power + self.add_noise(np.zeros(self.n_samples), 0.08)
        
        # Other variables
        roll_temp = 100 + 0.05 * slab_entry_temp + self.add_noise(np.zeros(self.n_samples), 5)
        coiler_speed = roll_speed * 0.98 + self.add_noise(np.zeros(self.n_samples), 0.02)
        uncoiler_speed = roll_speed * 1.02 + self.add_noise(np.zeros(self.n_samples), 0.02)
        tension_force = 500 + 50 * roll_speed + self.add_noise(np.zeros(self.n_samples), 20)
        thickness_entry = 50 + self.add_noise(np.ones(self.n_samples) * 50, 0.5)
        width = 1500 + self.add_noise(np.ones(self.n_samples) * 1500, 5)
        edge_quality = 90 + self.add_noise(np.ones(self.n_samples) * 90, 2)
        hydraulic_pressure = 200 + 0.01 * rolling_force + self.add_noise(np.zeros(self.n_samples), 5)
        cooling_water_temp = 25 + 0.01 * slab_exit_temp + self.add_noise(np.zeros(self.n_samples), 1)
        acoustic_level = 80 + 0.005 * motor_power + self.add_noise(np.zeros(self.n_samples), 2)
        
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'station_id': 'mill-01',
            'slab_entry_temp': slab_entry_temp,
            'slab_exit_temp': slab_exit_temp,
            'roll_temp': roll_temp,
            'roll_speed': roll_speed,
            'coiler_speed': coiler_speed,
            'uncoiler_speed': uncoiler_speed,
            'rolling_force': rolling_force,
            'tension_force': tension_force,
            'thickness_entry': thickness_entry,
            'thickness_exit': thickness_exit,
            'width': width,
            'flatness': flatness,
            'surface_quality_index': surface_quality_index,
            'edge_quality': edge_quality,
            'motor_power': motor_power,
            'hydraulic_pressure': hydraulic_pressure,
            'cooling_water_flow': cooling_water_flow,
            'cooling_water_temp': cooling_water_temp,
            'vibration_x': vibration_x,
            'vibration_y': vibration_y,
            'acoustic_level': acoustic_level
        })

    def generate_annealing_furnace_data(self) -> pd.DataFrame:
        """Generate data for Annealing Furnace station"""
        
        # Root causes
        heating_zone_temp = 750 + 20 * np.sin(2 * np.pi * np.arange(self.n_samples) / (24 * 60)) + \
                            self.add_noise(np.ones(self.n_samples) * 750, 0.02)
        strip_speed = 3.0 + 0.2 * np.random.randn(self.n_samples)
        hydrogen_concentration = 5.0 + 0.3 * np.random.randn(self.n_samples)
        gas_consumption = 1000 + 50 * np.random.randn(self.n_samples)
        
        # Causal relationships
        soaking_zone_temp = 0.95 * heating_zone_temp + 50 + self.add_noise(np.zeros(self.n_samples), 5)
        grain_size = 50 - 0.03 * soaking_zone_temp + self.add_noise(np.zeros(self.n_samples), 2)
        hardness = 150 + 0.5 * grain_size + self.add_noise(np.zeros(self.n_samples), 3)
        cooling_rate = 100 - 10 * strip_speed + self.add_noise(np.zeros(self.n_samples), 5)
        tensile_strength = 400 + 0.5 * cooling_rate + self.add_noise(np.zeros(self.n_samples), 10)
        surface_quality = 90 + 0.5 * hydrogen_concentration + self.add_noise(np.zeros(self.n_samples), 1)
        electricity_consumption = 500 + 0.3 * gas_consumption + self.add_noise(np.zeros(self.n_samples), 20)
        
        # Other variables
        cooling_zone_temp = 0.4 * soaking_zone_temp + self.add_noise(np.zeros(self.n_samples), 10)
        nitrogen_flow = 1000 + 50 * np.random.randn(self.n_samples)
        oxygen_ppm = 10 + 2 * np.random.randn(self.n_samples)
        furnace_throughput = 100 + 5 * strip_speed + self.add_noise(np.zeros(self.n_samples), 3)
        elongation = 25 - 0.05 * hardness + self.add_noise(np.zeros(self.n_samples), 1)
        heating_setpoint = 750 + self.add_noise(np.ones(self.n_samples) * 750, 5)
        strip_tension = 500 + 20 * strip_speed + self.add_noise(np.zeros(self.n_samples), 10)
        strip_position = 50 + self.add_noise(np.ones(self.n_samples) * 50, 2)
        furnace_pressure = 1.0 + self.add_noise(np.ones(self.n_samples) * 1.0, 0.02)
        production_rate = furnace_throughput * 0.95 + self.add_noise(np.zeros(self.n_samples), 2)
        yield_percentage = 95 + self.add_noise(np.ones(self.n_samples) * 95, 1)
        
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'station_id': 'anneal-01',
            'heating_zone_temp': heating_zone_temp,
            'soaking_zone_temp': soaking_zone_temp,
            'cooling_zone_temp': cooling_zone_temp,
            'hydrogen_concentration': hydrogen_concentration,
            'nitrogen_flow': nitrogen_flow,
            'oxygen_ppm': oxygen_ppm,
            'strip_speed': strip_speed,
            'furnace_throughput': furnace_throughput,
            'grain_size': grain_size,
            'hardness': hardness,
            'tensile_strength': tensile_strength,
            'elongation': elongation,
            'gas_consumption': gas_consumption,
            'electricity_consumption': electricity_consumption,
            'heating_setpoint': heating_setpoint,
            'cooling_rate': cooling_rate,
            'strip_tension': strip_tension,
            'strip_position': strip_position,
            'furnace_pressure': furnace_pressure,
            'production_rate': production_rate,
            'yield_percentage': yield_percentage,
            'surface_quality': surface_quality
        })

    def generate_all_stations(self, output_dir: str = "data/mock") -> dict:
        """Generate data for all stations and save to files"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating mock data from {self.start_date} for {self.days} days...")
        print(f"Frequency: {self.freq}, Total samples: {self.n_samples}")
        
        # Generate data for each station
        stations = {
            'furnace-01': self.generate_blast_furnace_data(),
            'mill-01': self.generate_rolling_mill_data(),
            'anneal-01': self.generate_annealing_furnace_data()
        }
        
        # Save individual station files
        for station_id, df in stations.items():
            csv_path = output_path / f"{station_id}_data.csv"
            df.to_csv(csv_path, index=False)
            print(f"✓ Saved {station_id}: {len(df)} records → {csv_path}")
        
        # Save combined file
        combined_df = pd.concat(stations.values(), ignore_index=True)
        combined_path = output_path / "all_stations_data.csv"
        combined_df.to_csv(combined_path, index=False)
        print(f"✓ Saved combined data: {len(combined_df)} records → {combined_path}")
        
        # Save metadata
        metadata = {
            'generation_date': datetime.now().isoformat(),
            'start_date': self.start_date.isoformat(),
            'days': self.days,
            'frequency': self.freq,
            'total_samples': self.n_samples,
            'stations': list(stations.keys()),
            'causal_relationships': self._get_causal_relationships()
        }
        
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Saved metadata → {metadata_path}")
        
        return stations

    def _get_causal_relationships(self) -> dict:
        """Document the ground truth causal relationships"""
        return {
            'furnace-01': [
                'hot_blast_temp → furnace_top_temp → pig_iron_production_rate',
                'oxygen_flow → carbon_content → iron_quality_index',
                'coal_injection_rate → fuel_consumption → power_consumption',
                'ore_feed_rate → slag_volume'
            ],
            'mill-01': [
                'slab_entry_temp → rolling_force → thickness_exit',
                'roll_speed → surface_quality_index',
                'cooling_water_flow → slab_exit_temp → flatness',
                'motor_power → vibration_x, vibration_y'
            ],
            'anneal-01': [
                'heating_zone_temp → soaking_zone_temp → grain_size → hardness',
                'strip_speed → cooling_rate → tensile_strength',
                'hydrogen_concentration → surface_quality',
                'gas_consumption → electricity_consumption'
            ]
        }


def main():
    """Main function to generate mock data"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate mock manufacturing data')
    parser.add_argument('--start-date', default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=180, help='Number of days to generate')
    parser.add_argument('--freq', default='1min', help='Sampling frequency (e.g., 1min, 30s, 1h)')
    parser.add_argument('--output', default='data/mock', help='Output directory')
    
    args = parser.parse_args()
    
    generator = ManufacturingDataGenerator(
        start_date=args.start_date,
        days=args.days,
        freq=args.freq
    )
    
    stations = generator.generate_all_stations(output_dir=args.output)
    
    print("\n" + "="*60)
    print("Mock data generation complete!")
    print("="*60)
    print(f"\nData location: {args.output}/")
    print("\nFiles created:")
    print("  - furnace-01_data.csv (Blast Furnace)")
    print("  - mill-01_data.csv (Rolling Mill)")
    print("  - anneal-01_data.csv (Annealing Furnace)")
    print("  - all_stations_data.csv (Combined)")
    print("  - metadata.json (Causal relationships & info)")
    print("\nNext steps:")
    print("  1. Load data: pd.read_csv('data/mock/furnace-01_data.csv')")
    print("  2. Run causal discovery on the data")
    print("  3. Compare discovered DAG with ground truth in metadata.json")


if __name__ == "__main__":
    main()
