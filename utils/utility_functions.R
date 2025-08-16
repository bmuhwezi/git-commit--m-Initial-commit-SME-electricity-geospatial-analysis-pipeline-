# ==============================================================================
# UTILITY FUNCTIONS MODULE
# Helper functions for validation, summaries, and analysis
# ==============================================================================

pacman::p_load(dplyr, tidyr)

# ==============================================================================
# 1. DATA VALIDATION
# ==============================================================================

#' Validate panel data structure
validate_panel_data <- function(df, id_var = "nis_rad", time_var = "Nof_Mths") {
  validation <- list(
    n_individuals = length(unique(df[[id_var]])),
    n_time_periods = length(unique(df[[time_var]])),
    n_observations = nrow(df)
  )
  
  validation$is_balanced <- validation$n_observations == (validation$n_individuals * validation$n_time_periods)
  
  # Missing data summary
  validation$missing_data <- df %>%
    summarise(across(everything(), ~sum(is.na(.x)))) %>%
    pivot_longer(everything(), names_to = "variable", values_to = "missing_count") %>%
    filter(missing_count > 0)
  
  # Data range checks
  numeric_vars <- df %>% select(where(is.numeric)) %>% names()
  validation$data_ranges <- df %>%
    summarise(across(all_of(numeric_vars), list(min = ~min(.x, na.rm = TRUE), max = ~max(.x, na.rm = TRUE)), .names = "{.col}_{.fn}"))
  
  validation
}

#' Check for outliers using IQR method
detect_outliers <- function(df, vars = NULL, iqr_multiplier = 1.5) {
  if (is.null(vars)) vars <- df %>% select(where(is.numeric)) %>% names()
  
  outlier_summary <- map_dfr(vars, ~{
    x <- df[[.x]]
    Q1 <- quantile(x, 0.25, na.rm = TRUE)
    Q3 <- quantile(x, 0.75, na.rm = TRUE)
    IQR <- Q3 - Q1
    
    lower_bound <- Q1 - iqr_multiplier * IQR
    upper_bound <- Q3 + iqr_multiplier * IQR
    
    outliers <- which(x < lower_bound | x > upper_bound)
    
    data.frame(
      variable = .x,
      n_outliers = length(outliers),
      outlier_rate = length(outliers) / length(x),
      lower_bound = lower_bound,
      upper_bound = upper_bound
    )
  })
  
  outlier_summary
}

# ==============================================================================
# 2. SUMMARY STATISTICS
# ==============================================================================

#' Create comprehensive summary statistics
create_summary_stats <- function(df, group_var = 'rural_urban', numeric_vars = NULL) {
  if (is.null(numeric_vars)) numeric_vars <- df %>% select(where(is.numeric)) %>% names()
  
  df %>%
    group_by(!!sym(group_var)) %>%
    summarise(
      across(all_of(numeric_vars), 
             list(mean = ~mean(.x, na.rm = TRUE),
                  median = ~median(.x, na.rm = TRUE),
                  sd = ~sd(.x, na.rm = TRUE),
                  min = ~min(.x, na.rm = TRUE),
                  max = ~max(.x, na.rm = TRUE)),
             .names = "{.col}_{.fn}"),
      n = n(),
      .groups = 'drop'
    )
}

#' Create correlation matrix
create_correlation_matrix <- function(df, vars = NULL, method = "pearson") {
  if (is.null(vars)) vars <- df %>% select(where(is.numeric)) %>% names()
  
  cor_matrix <- cor(df[vars], use = "complete.obs", method = method)
  
  # Convert to long format for easier viewing
  cor_long <- cor_matrix %>%
    as.data.frame() %>%
    rownames_to_column("var1") %>%
    pivot_longer(-var1, names_to = "var2", values_to = "correlation") %>%
    filter(var1 != var2) %>%
    arrange(desc(abs(correlation)))
  
  list(matrix = cor_matrix, long_format = cor_long)
}

#' Generate data quality report
generate_data_quality_report <- function(df, output_file = NULL) {
  
  report <- list(
    data_dimensions = dim(df),
    validation = validate_panel_data(df),
    outliers = detect_outliers(df),
    correlations = create_correlation_matrix(df),
    summary_stats = create_summary_stats(df)
  )
  
  # High correlations (> 0.7)
  report$high_correlations <- report$correlations$long_format %>%
    filter(abs(correlation) > 0.7) %>%
    arrange(desc(abs(correlation)))
  
  if (!is.null(output_file)) {
    cat("Data Quality Report\n", file = output_file)
    cat("==================\n\n", file = output_file, append = TRUE)
    
    cat("Data Dimensions:", report$data_dimensions[1], "rows x", report$data_dimensions[2], "columns\n\n", file = output_file, append = TRUE)
    
    cat("Panel Structure:\n", file = output_file, append = TRUE)
    cat("- Individuals:", report$validation$n_individuals, "\n", file = output_file, append = TRUE)
    cat("- Time periods:", report$validation$n_time_periods, "\n", file = output_file, append = TRUE)
    cat("- Balanced:", report$validation$is_balanced, "\n\n", file = output_file, append = TRUE)
    
    if (nrow(report$validation$missing_data) > 0) {
      cat("Missing Data:\n", file = output_file, append = TRUE)
      write.table(report$validation$missing_data, file = output_file, append = TRUE, row.names = FALSE)
      cat("\n", file = output_file, append = TRUE)
    }
    
    if (nrow(report$high_correlations) > 0) {
      cat("High Correlations (|r| > 0.7):\n", file = output_file, append = TRUE)
      write.table(report$high_correlations, file = output_file, append = TRUE, row.names = FALSE)
    }
  }
  
  report
}

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

#' Split data by location
split_by_location <- function(df) {
  list(
    urban = df[df$rural_urban == 'Urban', ],
    rural = df[df$rural_urban == 'Rural', ],
    combined = df
  )
}

#' Clean variable names for display
clean_var_names <- function(vars) {
  vars %>%
    str_replace_all('_', ' ') %>%
    str_to_title() %>%
    str_replace('Fsp', 'FSP') %>%
    str_replace('Gdp', 'GDP') %>%
    str_replace('Mins?', 'Min.') %>%
    str_replace('Kwh', 'kWh')
}

#' Create variable labels mapping
create_var_labels <- function() {
  list(
    csmo_fact = "Monthly kWh Consumption",
    total_structs = "Number of Structures",
    population = "Population Density",
    fsp = "Financial Service Providers",
    min_dist2_road = "Distance to Road (km)",
    Electrification = "Electrification Rate (%)",
    Night_Lights = "Night-time Illumination",
    GDP = "GDP per Capita",
    rural_urban = "Location Type",
    Year_of_connection = "Year of Connection",
    Nof_Mths = "Months Since Connection"
  )
}

#' Save analysis results
save_analysis_results <- function(results, output_dir, prefix = "analysis") {
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  # Save different components
  if ("models" %in% names(results)) {
    saveRDS(results$models, file.path(output_dir, paste0(prefix, "_models.rds")))
  }
  
  if ("plots" %in% names(results)) {
    saveRDS(results$plots, file.path(output_dir, paste0(prefix, "_plots.rds")))
  }
  
  if ("summary_stats" %in% names(results)) {
    write.csv(results$summary_stats, file.path(output_dir, paste0(prefix, "_summary_stats.csv")), row.names = FALSE)
  }
  
  if ("data_quality" %in% names(results)) {
    generate_data_quality_report(results$data_quality, file.path(output_dir, paste0(prefix, "_data_quality.txt")))
  }
  
  cat("Results saved to:", output_dir, "\n")
}

#' Load analysis results
load_analysis_results <- function(output_dir, prefix = "analysis") {
  results <- list()
  
  models_file <- file.path(output_dir, paste0(prefix, "_models.rds"))
  if (file.exists(models_file)) results$models <- readRDS(models_file)
  
  plots_file <- file.path(output_dir, paste0(prefix, "_plots.rds"))
  if (file.exists(plots_file)) results$plots <- readRDS(plots_file)
  
  summary_file <- file.path(output_dir, paste0(prefix, "_summary_stats.csv"))
  if (file.exists(summary_file)) results$summary_stats <- read.csv(summary_file)
  
  results
}

#' Time execution of function
time_execution <- function(expr, description = "") {
  start_time <- Sys.time()
  result <- expr
  end_time <- Sys.time()
  
  elapsed <- end_time - start_time
  cat(description, "completed in", round(elapsed, 2), attr(elapsed, "units"), "\n")
  
  result
}

# ==============================================================================
# 4. SIMPLIFIED FUNCTIONS (NO CONFIG NEEDED)
# ==============================================================================

#' Time execution of function
time_execution <- function(expr, description = "") {
  start_time <- Sys.time()
  result <- expr
  end_time <- Sys.time()
  
  elapsed <- end_time - start_time
  cat(description, "completed in", round(elapsed, 2), attr(elapsed, "units"), "\n")
  
  result
}

#' Save analysis results to directory
save_results <- function(results, output_dir = "results/", prefix = "analysis") {
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  
  if ("models" %in% names(results)) {
    saveRDS(results$models, file.path(output_dir, paste0(prefix, "_models_", timestamp, ".rds")))
  }
  
  if ("plots" %in% names(results)) {
    saveRDS(results$plots, file.path(output_dir, paste0(prefix, "_plots_", timestamp, ".rds")))
  }
  
  if ("summary_stats" %in% names(results)) {
    write.csv(results$summary_stats, file.path(output_dir, paste0(prefix, "_summary_", timestamp, ".csv")), row.names = FALSE)
  }
  
  cat("Results saved to:", output_dir, "\n")
}