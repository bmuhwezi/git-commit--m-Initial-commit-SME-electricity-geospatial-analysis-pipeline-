# Effects of Complementary Infrastructure on SME Electricity Consumption in Kenya
A comprehensive geospatial analysis pipeline for examining Small and Medium Enterprise (SME) electricity consumption patterns in Kenya using multiple spatial features.

## Overview

This repository contains code and tools for analyzing the relationship between SME electricity consumption and various geospatial factors including population density, road access, financial service providers, building structures, and nighttime lights. The analysis uses 5+ years of electricity billing data from grid-connected SMEs across Kenya.

## Key Features

- **Geospatial Feature Extraction**: Extract features within 500m buffers around each SME location
- **Parallel Processing**: SLURM-based cluster computing for large-scale data processing
- **Multiple Data Sources**: Integration of satellite imagery, census data, and utility records
- **Panel Data Regression**: Perfomes panel data Fixed Effects regression

## Repository Structure

```
Kenya-sme-electricity-geospatial-analysis/
├── README.md
├── requirements.txt
├── config.py                    # Configuration and file paths
├── main.py                      # Main pipeline orchestrator
├── main.R                      # Main pipeline orchestrator
│
├── feature_extraction/
│   ├── fsp_extraction.py        # Financial service providers
│   ├── population_extraction.py # Population density (WorldPop)
│   ├── roads_extraction.py      # Road access and length
│   ├── nightlights_extraction.py# VIIRS nighttime lights
│   └── slurm_scripts/           # SLURM job submission scripts
│       ├── fsp_array.sh
│       ├── population_array.sh
│       ├── roads_array.sh
│       └── nightlights_array.sh
│ 
├── utils/
│   ├── data_processing.R         # Data preprocessing utilities
│   ├── utility_functions.R         # Data preprocessing utilities
│   ├── data_cleaning.py         # Data preprocessing utilities
│   ├── spatial_utils.py         # Spatial calculation functions
│   └── file_utils.py            # File I/O operations
│
├── visualizations/
│   ├── visualizations.py         # Plotting graphs python script
│   └── visualization.R          # Plotting graphs R script
│
└── analysis/
    ├── regression_models.R      # Contains panel data regression functions
    ├── consumption_analyzer.py  # Consumption pattern analysis
    ├── clustering_analysis.py   # Customer segmentation
    └── rural_urban_classifier.py# Geographic classification


    
```

## Data Sources

### Primary Datasets
- **A2 Locations** (`A1locs.pck`): SME locations with coordinates and connection dates
- **A2 Bills** (`A1_bills.csv`): Monthly electricity consumption records (5+ years)

### Geospatial Features
- **Financial Service Providers**: Bank and mobile money locations
- **Population Density**: WorldPop gridded population data
- **Road Networks**: Kenya roads shapefile with classification
- **Building Structures**: Locations of all structures
- **Nighttime Lights**: VIIRS monthly composite imagery
- **Electrified Structures**: Grid-connected buildings and transformers

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/Kenya-sme-electricity-geospatial-analysis.git
cd Kenya-sme-electricity-geospatial-analysis
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure paths**:
   - Update file paths in `config.py` to match your system
   - Ensure all input datasets are accessible

## Usage

### 1. Quick Start
```bash
# Run the complete pipeline
python main.py
```

### 2. Feature Extraction on Compute Cluster

Submit SLURM jobs for parallel feature extraction:

```bash
# Financial service providers
sbatch feature_extraction/slurm_scripts/fsp_array.sh

# Population density  
sbatch feature_extraction/slurm_scripts/population_array.sh

# Road access
sbatch feature_extraction/slurm_scripts/roads_array.sh

# Nighttime lights
sbatch feature_extraction/slurm_scripts/nightlights_array.sh
```

### 3. Manual Feature Extraction

Run individual feature extraction scripts:

```bash
# Extract FSP features for chunk 0
python feature_extraction/fsp_extraction.py 0

# Extract population features for chunk 5
python feature_extraction/population_extraction.py 5
```

## Key Parameters

- **Buffer Radius**: 500 meters around each SME location
- **Processing Chunks**: 36 parallel chunks for cluster processing
- **Time Period**: 2010-2020 electricity consumption data
- **Spatial Resolution**: Varies by data source (30m-1km)

## Output

The pipeline generates:

1. **`DF_features.csv`**: Final panel dataset ready for econometric analysis
2. **Feature-specific datasets**: Individual feature extractions in `/outputs/features/`
3. **Visualizations**: Consumption patterns and spatial distributions
4. **Summary statistics**: Data quality and coverage reports

## Pipeline Workflow

1. **Data Loading**: Load A2 locations and billing data
2. **Data Cleaning**: Remove outliers, handle missing values, standardize formats
3. **Feature Extraction**: Extract geospatial features using parallel processing
4. **Data Integration**: Combine all features into single analysis dataset
5. **Quality Control**: Validate data completeness and consistency

## Technical Requirements

- **Python 3.7+**
- **Geospatial libraries**: GeoPandas, Rasterio, Shapely, GDAL
- **Scientific computing**: Pandas, NumPy, SciPy
- **Cluster computing**: SLURM workload manager
- **Memory**: 10GB+ RAM per process for large raster operations

## Performance

- **Processing time**: ~2-4 hours on 36-core cluster
- **Memory usage**: ~10GB per chunk for raster operations  
- **Output size**: ~500MB final dataset
- **Scalability**: Designed for 10,000+ SME locations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-analysis`)
3. Make changes and test thoroughly
4. Commit changes (`git commit -am 'Add new spatial feature'`)
5. Push to branch (`git push origin feature/new-analysis`)
6. Create Pull Request

