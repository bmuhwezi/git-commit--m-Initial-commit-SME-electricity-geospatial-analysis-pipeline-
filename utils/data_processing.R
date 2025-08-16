# ==============================================================================
# DATA PROCESSING MODULE
# Compact data loading and preprocessing functions
# ==============================================================================

pacman::p_load(dplyr, BBmisc, reticulate)

# Set default file paths
DEFAULT_PATHS <- list(
  features_data = "/Users/bmuhwezi/Box Sync/Research/scp_downloads/features_df3.pck",
  gcp_data = "/Users/bmuhwezi/Box Sync/Research/Energy4growth_hub/regression_df_with_monthlyGCP.pck",
  output_dir = "results/"
)

# ==============================================================================
# 1. DATA LOADING
# ==============================================================================

#' Load and clean main dataset
load_main_data <- function(data_path = DEFAULT_PATHS$features_data, fsp_categories = c("Agricultural", "capital_markets", "Insuarance", "Mobile_Money_agents", "Post_Office", "bank_agents", "development_finance", "Microfinance_banks", "Money_transer_service", "SACCO", "commercial_bank", "Hire_puchance", "Microfinance_Institutions", "Pension_Provider", "Stand_alone_ATMs")) {
  
  source_python("pickle_reader.py")
  raw_data <- read_pickle_file(data_path)
  
  # Clean and transform data
  raw_data$min_dist2_road <- raw_data$min_dist2_road * 111.32  # Convert to km
  raw_data$fsp <- rowSums(raw_data[intersect(fsp_categories, names(raw_data))], na.rm = TRUE)
  raw_data$total_structs[is.na(raw_data$total_structs)] <- 0
  raw_data$Night_Lights[raw_data$Night_Lights < 0] <- 0
  raw_data$Electrification <- raw_data$Electrification * 100  # Convert to percentage
  
  # Remove invalid observations
  invalid_ids <- unique(filter(raw_data, Electrification > 100)$nis_rad)
  if (length(invalid_ids) > 0) raw_data <- filter(raw_data, !nis_rad %in% invalid_ids)
  
  raw_data
}

#' Load and merge GCP data
merge_gcp_data <- function(df, gcp_path = DEFAULT_PATHS$gcp_data) {
  source_python("pickle_reader.py")
  
  df$Year_of_connection[df$Year_of_connection < 2010] <- 2009
  df[c("Year_of_connection", "Nof_Mths", "nis_rad")] <- lapply(df[c("Year_of_connection", "Nof_Mths", "nis_rad")], as.factor)
  
  gcp_data <- read_pickle_file(gcp_path)
  df_merged <- merge(df, gcp_data[, c('nis_rad', 'Nof_Mths', 'GCP')], by = c('nis_rad', 'Nof_Mths'))
  
  df_merged$GCP <- as.numeric(df_merged$GCP)
  df_merged <- df_merged[!is.na(df_merged$GCP), ]
  
  # Rename GDP columns
  if ("GDP" %in% names(df_merged)) names(df_merged)[names(df_merged) == "GDP"] <- "GDP_annual"
  names(df_merged)[names(df_merged) == "GCP"] <- "GDP"
  
  df_merged
}

# ==============================================================================
# 2. SAMPLING
# ==============================================================================

#' Sample balanced panel by year of connection
sample_balanced_panel <- function(df, sample_size = 30000, rural_prop = 0.59) {
  df <- df[!is.na(df$GDP), ]
  
  # Calculate missing bills by group
  df_summary <- df %>%
    group_by(nis_rad, rural_urban, Year_of_connection) %>%
    summarise(nof_M = max(Nof_Mths) - min(Nof_Mths), count = n(), .groups = 'drop') %>%
    mutate(dff = count - nof_M) %>%
    filter(dff >= 0)
  
  # Sample by location
  sample_by_location <- function(location_data, target_size) {
    location_data$Year_of_connection[location_data$Year_of_connection < 2009] <- 2009
    
    year_weights <- location_data %>%
      group_by(Year_of_connection) %>%
      summarise(weight = n() / nrow(location_data), .groups = 'drop')
    
    set.seed(1)
    sampled_ids <- unlist(map(seq_len(nrow(year_weights)), ~{
      year_data <- filter(location_data, Year_of_connection == year_weights$Year_of_connection[.x])
      sample_size_year <- round(year_weights$weight[.x] * target_size)
      if (nrow(year_data) >= sample_size_year) {
        sample(year_data$nis_rad, sample_size_year)
      } else NULL
    }))
  }
  
  rural_ids <- sample_by_location(filter(df_summary, rural_urban == 'Rural'), sample_size * rural_prop)
  urban_ids <- sample_by_location(filter(df_summary, rural_urban == 'Urban'), sample_size * (1 - rural_prop))
  
  filter(df, nis_rad %in% c(rural_ids, urban_ids))
}

# ==============================================================================
# 3. VARIABLE CREATION
# ==============================================================================

#' Create all dummy variables
create_all_dummies <- function(df, vars = c('population', 'total_structs', 'Electrification', 'fsp', 'Night_Lights', 'min_dist2_road')) {
  
  for (var in vars) {
    if (var %in% names(df)) {
      dummy_name <- paste0(var, "_dummy")
      df[[dummy_name]] <- ifelse(var == "min_dist2_road", "Low", "High")
      
      mdn_urban <- median(df[df$rural_urban == 'Urban', var], na.rm = TRUE)
      mdn_rural <- median(df[df$rural_urban == 'Rural', var], na.rm = TRUE)
      
      if (var == "min_dist2_road") {
        df[(df[[var]] < mdn_urban) & (df$rural_urban == 'Urban'), dummy_name] <- "High"
        df[(df[[var]] < mdn_rural) & (df$rural_urban == 'Rural'), dummy_name] <- "High"
      } else {
        df[(df[[var]] < mdn_urban) & (df$rural_urban == 'Urban'), dummy_name] <- "Low"
        df[(df[[var]] < mdn_rural) & (df$rural_urban == 'Rural'), dummy_name] <- "Low"
      }
      
      df[[dummy_name]] <- factor(df[[dummy_name]], levels = c('Low', 'High'))
    }
  }
  df
}

#' Apply transformations
apply_transformations <- function(df, log_vars = c('csmo_fact', 'min_dist2_road', 'Night_Lights', 'population', 'Electrification', 'GDP', 'total_structs', 'fsp'), log_constant = 0.1, standardize = TRUE) {
  
  # Log transformation
  df_log <- df
  df_log[log_vars] <- lapply(df_log[log_vars], function(x) log(x + log_constant))
  
  # Standardization
  if (standardize) {
    df <- normalize(df, method = "standardize")
    df_log <- normalize(df_log, method = "standardize")
  }
  
  list(original = df, log_transformed = df_log)
}

# ==============================================================================
# 4. COMPLETE PIPELINE
# ==============================================================================

#' Run complete data processing pipeline
process_data_pipeline <- function(raw_data_path = DEFAULT_PATHS$features_data, gcp_data_path = DEFAULT_PATHS$gcp_data, sample_size = 40000, rural_prop = 0.59) {
  
  cat("Loading and cleaning data...\n")
  raw_data <- load_main_data(raw_data_path)
  
  cat("Sampling data...\n")
  sampled_data <- sample_balanced_panel(raw_data, sample_size, rural_prop)
  
  cat("Creating dummy variables...\n")
  processed_data <- create_all_dummies(sampled_data)
  
  cat("Merging GCP data...\n")
  final_data <- merge_gcp_data(processed_data, gcp_data_path)
  
  cat("Applying transformations...\n")
  transformed_data <- apply_transformations(final_data)
  
  # Split by location
  datasets <- list(
    raw = list(
      urban = final_data[final_data$rural_urban == 'Urban', ],
      rural = final_data[final_data$rural_urban == 'Rural', ],
      combined = final_data
    ),
    standardized = list(
      urban = transformed_data$original[transformed_data$original$rural_urban == 'Urban', ],
      rural = transformed_data$original[transformed_data$original$rural_urban == 'Rural', ],
      combined = transformed_data$original
    ),
    log_standardized = list(
      urban = transformed_data$log_transformed[transformed_data$log_transformed$rural_urban == 'Urban', ],
      rural = transformed_data$log_transformed[transformed_data$log_transformed$rural_urban == 'Rural', ],
      combined = transformed_data$log_transformed
    )
  )
  
  cat("Data processing complete!\n")
  datasets
}