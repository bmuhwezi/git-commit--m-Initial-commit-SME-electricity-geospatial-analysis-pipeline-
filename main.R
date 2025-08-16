# ==============================================================================
# MAIN ANALYSIS SCRIPT
# ==============================================================================

# Clear environment and load modules
rm(list = ls())
source("utility_functions.R")
source("data_processing.R")
source("visualization_functions.R")
source("regression_functions.R")

# ==============================================================================
# DIRECT FILE PATHS AND PARAMETERS
# ==============================================================================

# Paths
RAW_DATA_PATH <- "/Users/bmuhwezi/Box Sync/Research/scp_downloads/features_df3.pck"
GCP_DATA_PATH <- "/Users/bmuhwezi/Box Sync/Research/Energy4growth_hub/regression_df_with_monthlyGCP.pck"
OUTPUT_DIR <- "results/"

# Analysis parameters
SAMPLE_SIZE <- 40000
RURAL_PROPORTION <- 0.59
MAX_MONTHS_PLOT <- 120

# Variable definitions
CONTINUOUS_VARS <- c('total_structs', 'min_dist2_road', 'fsp', 'population', 'Electrification', 'Night_Lights', 'GDP')
TIME_VARYING_VARS <- c('fsp', 'population', 'Night_Lights', 'GDP')
TIME_INVARIANT_VARS <- c('Electrification', 'total_structs', 'min_dist2_road')

# ==============================================================================
# MAIN ANALYSIS PIPELINE
# ==============================================================================

main_analysis <- function(raw_data_path = RAW_DATA_PATH, 
                          gcp_data_path = GCP_DATA_PATH,
                          output_dir = OUTPUT_DIR,
                          sample_size = SAMPLE_SIZE,
                          rural_prop = RURAL_PROPORTION,
                          run_plots = TRUE, 
                          run_regressions = TRUE) {
  
  cat("=== ELECTRICITY CONSUMPTION ANALYSIS ===\n")
  
  # Check if files exist
  if (!file.exists(raw_data_path)) stop("Raw data file not found: ", raw_data_path)
  if (!file.exists(gcp_data_path)) stop("GCP data file not found: ", gcp_data_path)
  
  # 1. Data Processing
  cat("\n1. DATA PROCESSING\n")
  datasets <- time_execution(
    process_data_pipeline(raw_data_path, gcp_data_path, sample_size, rural_prop),
    "Data processing"
  )
  
  # 2. Data Quality Assessment
  cat("\n2. DATA QUALITY ASSESSMENT\n")
  data_quality <- time_execution(
    generate_data_quality_report(datasets$raw$combined),
    "Data quality assessment"
  )
  
  # 3. Descriptive Analysis
  cat("\n3. DESCRIPTIVE STATISTICS\n")
  summary_stats <- time_execution(
    create_summary_stats(datasets$raw$combined, numeric_vars = CONTINUOUS_VARS),
    "Summary statistics"
  )
  
  results <- list(
    datasets = datasets,
    data_quality = data_quality,
    summary_stats = summary_stats
  )
  
  # 4. Visualization
  if (run_plots) {
    cat("\n4. CREATING VISUALIZATIONS\n")
    plots <- time_execution({
      list(
        median_consumption = plot_median_consumption(datasets$raw$combined, MAX_MONTHS_PLOT),
        median_by_location = plot_median_by_location(datasets$raw$combined, MAX_MONTHS_PLOT),
        consumption_by_year = plot_consumption_by_year(datasets$raw$combined, max_months = MAX_MONTHS_PLOT),
        seasonal_patterns = if("Month" %in% names(datasets$raw$combined)) plot_consumption_calendar(datasets$raw$combined) else NULL,
        distributions = plot_cumulative_distributions(datasets$raw$combined),
        histograms = plot_distribution_histograms(datasets$raw$combined),
        segment_analysis = map(c("fsp_dummy", "Electrification_dummy", "population_dummy"), 
                               ~plot_consumption_segments(datasets$raw$combined, .x, max_months = MAX_MONTHS_PLOT)),
        interactions = plot_all_interactions(datasets$raw$combined, output_dir = file.path(output_dir, "interaction_plots"))
      )
    }, "Visualization creation")
    
    results$plots <- plots
  }
  
  # 5. Regression Analysis
  if (run_regressions) {
    cat("\n5. REGRESSION ANALYSIS\n")
    
    # Basic regressions
    cat("Running basic panel regressions...\n")
    basic_models <- time_execution(
      run_panel_regression(datasets$standardized$urban, datasets$standardized$rural, predictors = CONTINUOUS_VARS),
      "Basic panel regressions"
    )
    
    # Advanced methods
    cat("Running advanced econometric methods...\n")
    advanced_models <- time_execution({
      list(
        mundlak_urban = mundlak_estimation(datasets$standardized$urban, time_varying = TIME_VARYING_VARS, time_invariant = TIME_INVARIANT_VARS),
        mundlak_rural = mundlak_estimation(datasets$standardized$rural, time_varying = TIME_VARYING_VARS, time_invariant = TIME_INVARIANT_VARS),
        dummy_effects_urban = analyze_dummy_effects(datasets$standardized$urban),
        dummy_effects_rural = analyze_dummy_effects(datasets$standardized$rural),
        interactions_urban = analyze_dummy_interactions(datasets$standardized$urban),
        interactions_rural = analyze_dummy_interactions(datasets$standardized$rural),
        subsample_analysis_urban = analyze_subsamples(datasets$standardized$urban),
        subsample_analysis_rural = analyze_subsamples(datasets$standardized$rural)
      )
    }, "Advanced econometric methods")
    
    # Log-transformed models
    cat("Running log-transformed models...\n")
    log_models <- time_execution({
      list(
        mundlak_log_urban = mundlak_estimation(datasets$log_standardized$urban, time_varying = TIME_VARYING_VARS, time_invariant = TIME_INVARIANT_VARS),
        mundlak_log_rural = mundlak_estimation(datasets$log_standardized$rural, time_varying = TIME_VARYING_VARS, time_invariant = TIME_INVARIANT_VARS)
      )
    }, "Log-transformed models")
    
    results$models <- list(
      basic = basic_models,
      advanced = advanced_models,
      log_transformed = log_models
    )
  }
  
  # 6. Save Results
  cat("\n6. SAVING RESULTS\n")
  time_execution(
    save_results(results, output_dir, "electricity_analysis"),
    "Saving results"
  )
  
  cat("\n=== ANALYSIS COMPLETE ===\n")
  cat("Results saved to:", output_dir, "\n")
  
  return(results)
}

# ==============================================================================
# QUICK ANALYSIS FUNCTIONS
# ==============================================================================

#' Quick exploratory analysis
quick_analysis <- function(raw_data_path = RAW_DATA_PATH, gcp_data_path = GCP_DATA_PATH) {
  
  cat("=== QUICK EXPLORATORY ANALYSIS ===\n")
  
  # Load and process data
  datasets <- process_data_pipeline(raw_data_path, gcp_data_path, sample_size = 10000)
  
  # Basic plots
  plots <- list(
    median_consumption = plot_median_consumption(datasets$raw$combined),
    distributions = plot_cumulative_distributions(datasets$raw$combined)
  )
  
  # Basic stats
  stats <- create_summary_stats(datasets$raw$combined)
  
  # Simple regression
  basic_model <- run_panel_regression(datasets$standardized$urban, datasets$standardized$rural)
  
  list(datasets = datasets, plots = plots, stats = stats, model = basic_model)
}

#' Run only visualizations
run_plots_only <- function(raw_data_path = RAW_DATA_PATH, gcp_data_path = GCP_DATA_PATH, output_dir = OUTPUT_DIR) {
  
  datasets <- process_data_pipeline(raw_data_path, gcp_data_path)
  
  plots <- list(
    median_consumption = plot_median_consumption(datasets$raw$combined),
    median_by_location = plot_median_by_location(datasets$raw$combined),
    distributions = plot_cumulative_distributions(datasets$raw$combined),
    segments = plot_consumption_segments(datasets$raw$combined, "fsp_dummy")
  )
  
  # Save plots
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  map2(plots, names(plots), ~{
    ggsave(file.path(output_dir, paste0(.y, ".png")), .x, width = 10, height = 6, dpi = 300)
  })
  
  cat("Plots saved to:", output_dir, "\n")
  plots
}

#' Run only regressions
run_regressions_only <- function(raw_data_path = RAW_DATA_PATH, gcp_data_path = GCP_DATA_PATH) {
  
  datasets <- process_data_pipeline(raw_data_path, gcp_data_path)
  
  models <- list(
    basic = run_panel_regression(datasets$standardized$urban, datasets$standardized$rural),
    mundlak_urban = mundlak_estimation(datasets$standardized$urban),
    mundlak_rural = mundlak_estimation(datasets$standardized$rural),
    interactions = analyze_dummy_interactions(datasets$standardized$urban)
  )
  
  models
}

# ==============================================================================
# EXECUTION
# ==============================================================================

# results <- main_analysis()

# Or run specific components:
# quick_results <- quick_analysis()
# plots <- run_plots_only()
# models <- run_regressions_only()

# Example usage with custom paths:
# results <- main_analysis(
#   raw_data_path = "path/to/your/features_df3.pck",
#   gcp_data_path = "path/to/your/regression_df_with_monthlyGCP.pck",
#   output_dir = "custom_results/",
#   sample_size = 20000
# )