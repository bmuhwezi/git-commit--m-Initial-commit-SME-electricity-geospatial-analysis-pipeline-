# ==============================================================================
# REGRESSION FUNCTIONS MODULE
# ==============================================================================

pacman::p_load(AER, stargazer, plm, dplyr, BBmisc)

# ==============================================================================
# 1. DATA PREPARATION
# ==============================================================================

#' Create dummy variables based on rural/urban median split
create_dummy_variable <- function(df, var, dummy_name = paste0(var, "_dummy")) {
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
  df
}

#' Apply log transformation with constant
apply_log_transform <- function(df, vars = c('csmo_fact', 'min_dist2_road', 'Night_Lights', 'population', 'Electrification', 'GDP', 'total_structs', 'fsp'), constant = 0.1) {
  df[vars] <- lapply(df[vars], function(x) log(x + constant))
  df
}

#' Calculate cluster means for CRE
get_cluster_means <- function(df, time_varying_vars = c('fsp', 'population', 'Night_Lights', 'GDP')) {
  cluster_means <- df %>%
    group_by(nis_rad) %>%
    summarise(across(all_of(time_varying_vars), ~ mean(.x, na.rm = TRUE), .names = "{.col}_mean"), .groups = 'drop')
  
  df_merged <- df %>% left_join(cluster_means, by = 'nis_rad')
  
  for (var in time_varying_vars) {
    df_merged[[var]] <- df_merged[[var]] - df_merged[[paste0(var, "_mean")]]
  }
  
  df_merged
}

# ==============================================================================
# 2. CORE REGRESSION FUNCTIONS
# ==============================================================================

#' Run comprehensive panel regression analysis
run_panel_regression <- function(df_urban, df_rural, outcome = 'csmo_fact', predictors = c('total_structs', 'min_dist2_road', 'fsp', 'population', 'Electrification', 'Night_Lights', 'GDP')) {
  
  formula_obj <- as.formula(paste(outcome, "~", paste(predictors, collapse = " + ")))
  
  models <- list(
    pool_u = plm(formula_obj, df_urban, model = "pooling", index = c("nis_rad", "Nof_Mths")),
    pool_r = plm(formula_obj, df_rural, model = "pooling", index = c("nis_rad", "Nof_Mths")),
    re_u = plm(formula_obj, df_urban, model = "random", index = c("nis_rad", "Nof_Mths")),
    re_r = plm(formula_obj, df_rural, model = "random", index = c("nis_rad", "Nof_Mths")),
    fe_u = plm(formula_obj, df_urban, model = "within", index = c("nis_rad", "Nof_Mths")),
    fe_r = plm(formula_obj, df_rural, model = "within", index = c("nis_rad", "Nof_Mths"))
  )
  
  stargazer(models, type = 'text', column.labels = names(models))
  models
}

#' Mundlak (CRE) estimation
mundlak_estimation <- function(df, outcome = 'csmo_fact', time_varying = c('fsp', 'population', 'Night_Lights', 'GDP'), time_invariant = c('Electrification', 'total_structs', 'min_dist2_road')) {
  
  df_cre <- get_cluster_means(df, time_varying)
  
  predictors <- c(time_varying, time_invariant, paste0(time_varying, "_mean"))
  if ("Year_of_connection" %in% names(df_cre)) predictors <- c(predictors, "Year_of_connection")
  
  formula_obj <- as.formula(paste(outcome, "~", paste(predictors, collapse = " + ")))
  
  plm(formula_obj, df_cre, model = "random", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
}

#' Between estimator for time-invariant effects
between_estimation <- function(df, outcome = 'csmo_fact', predictors = c('fsp', 'population', 'Night_Lights', 'Electrification', 'total_structs', 'min_dist2_road')) {
  
  formula_obj <- as.formula(paste(outcome, "~", paste(predictors, collapse = " + ")))
  
  plm(formula_obj, df, model = "between", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
}

# ==============================================================================
# 3. INTERACTION AND DUMMY ANALYSIS
# ==============================================================================

#' Analyze dummy variable effects
analyze_dummy_effects <- function(df, dummy_vars = c("Electrification_dummy", "dist2_road_dummy", "population_dummy", "structs_dummy", "NL_dummy", "fsp_dummy"), base_controls = c('Night_Lights', 'fsp', 'min_dist2_road', 'population', 'total_structs', 'GDP')) {
  
  models <- map(dummy_vars, ~{
    controls <- setdiff(base_controls, gsub("_dummy", "", .x))
    formula_str <- paste("csmo_fact ~", paste(c(controls, .x), collapse = " + "))
    plm(as.formula(formula_str), df, model = "random", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
  })
  
  names(models) <- gsub("_dummy", "", dummy_vars)
  stargazer(models, type = 'text', column.labels = names(models))
  models
}

#' High/Low subsample analysis
analyze_subsamples <- function(df, dummy_vars = c("Electrification_dummy", "dist2_road_dummy", "population_dummy", "structs_dummy", "NL_dummy", "fsp_dummy"), base_formula = "csmo_fact ~ Night_Lights + fsp + min_dist2_road + population + total_structs + GDP") {
  
  models <- map(dummy_vars, ~{
    controls <- setdiff(c('Night_Lights', 'fsp', 'min_dist2_road', 'population', 'total_structs', 'GDP'), gsub("_dummy", "", .x))
    formula_obj <- as.formula(paste("csmo_fact ~", paste(controls, collapse = " + ")))
    
    low_model <- plm(formula_obj, filter(df, !!sym(.x) == "Low"), model = "random", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
    high_model <- plm(formula_obj, filter(df, !!sym(.x) == "High"), model = "random", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
    
    list(low = low_model, high = high_model)
  })
  
  names(models) <- gsub("_dummy", "", dummy_vars)
  
  # Flatten for stargazer
  flat_models <- unlist(models, recursive = FALSE)
  stargazer(flat_models, type = 'text')
  models
}

#' Dummy interaction analysis
analyze_dummy_interactions <- function(df, interactions = list(c("Electrification_dummy", "dist2_road_dummy"), c("fsp_dummy", "dist2_road_dummy"), c("population_dummy", "structs_dummy"))) {
  
  df_cre <- get_cluster_means(df)
  
  models <- map(interactions, ~{
    var1 <- .x[1]
    var2 <- .x[2]
    
    # Create interaction term
    base_vars <- setdiff(c('Night_Lights', 'fsp', 'min_dist2_road', 'population', 'total_structs', 'GDP'), 
                         gsub("_dummy", "", c(var1, var2)))
    
    formula_str <- paste("csmo_fact ~", paste(c(base_vars, paste(var1, var2, sep = "*")), collapse = " + "))
    plm(as.formula(formula_str), df_cre, model = "random", random.method = "walhus", index = c("nis_rad", "Nof_Mths"))
  })
  
  names(models) <- map_chr(interactions, ~paste(gsub("_dummy", "", .x), collapse = "_x_"))
  stargazer(models, type = 'text', column.labels = names(models))
  models
}

# ==============================================================================
# 4. ADVANCED METHODS
# ==============================================================================

#' Newey-West estimation with HAC standard errors
newey_west_estimation <- function(df, formula_str = "csmo_fact ~ Night_Lights + Electrification + fsp + min_dist2_road + population * total_structs + GDP") {
  
  re_model <- plm(as.formula(formula_str), df, model = "random", index = c("nis_rad", "Nof_Mths"))
  coeftest(re_model, vcov. = vcovNW)
}

#' Cochrane-Orcutt type procedure for serial correlation
cochrane_orcutt_procedure <- function(df, formula_str = "csmo_fact ~ total_structs + min_dist2_road + fsp + population + Electrification + Night_Lights + GDP") {
  
  # Initial random effects model
  re_model <- plm(as.formula(formula_str), df, model = "random", index = c("nis_rad", "Nof_Mths"))
  
  # Get residuals and estimate AR(1) parameter
  df$residuals <- re_model$residuals
  aux_model <- plm(residuals ~ lag(residuals) + total_structs + min_dist2_road + fsp + population + Electrification + Night_Lights + GDP, 
                   df, model = "random", index = c("nis_rad", "Nof_Mths"))
  
  rho_hat <- aux_model$coefficients[1]
  
  # Transform variables and re-estimate
  transformed_formula <- paste("I(csmo_fact - rho_hat * lag(csmo_fact)) ~",
                               "I(total_structs - rho_hat * lag(total_structs)) +",
                               "I(min_dist2_road - rho_hat * lag(min_dist2_road)) +",
                               "I(fsp - rho_hat * lag(fsp)) +",
                               "I(population - rho_hat * lag(population)) +",
                               "I(Electrification - rho_hat * lag(Electrification)) +",
                               "I(Night_Lights - rho_hat * lag(Night_Lights)) +",
                               "I(GDP - rho_hat * lag(GDP))")
  
  transformed_model <- plm(as.formula(transformed_formula), df, model = "random", index = c("nis_rad", "Nof_Mths"))
  
  stargazer(re_model, transformed_model, type = 'text', column.labels = c("Original", "Transformed"))
  list(original = re_model, transformed = transformed_model, rho = rho_hat)
}

#' Two-stage estimation comparing FE and between estimators
two_stage_estimation <- function(df) {
  
  # Stage 1: Fixed effects
  fe_model <- plm(csmo_fact ~ fsp + population + Night_Lights + GDP + Electrification + total_structs + min_dist2_road, 
                  df, model = "within", index = c("nis_rad", "Nof_Mths"))
  
  # Extract fixed effects
  fixed_effects <- data.frame(FE = fixef(fe_model), nis_rad = names(fixef(fe_model)))
  
  # Stage 2: Between regression on fixed effects
  df_fe <- df %>% 
    select(Year_of_connection, Electrification, total_structs, min_dist2_road, nis_rad, Nof_Mths) %>%
    left_join(fixed_effects, by = "nis_rad")
  
  between_model <- plm(FE ~ Electrification + total_structs + min_dist2_road, 
                       df_fe, model = "between", index = c("nis_rad", "Nof_Mths"))
  
  # Compare with Mundlak
  mundlak_model <- mundlak_estimation(df)
  
  stargazer(fe_model, between_model, mundlak_model, type = 'text', 
            column.labels = c("FE", "Between", "Mundlak"))
  
  list(fe = fe_model, between = between_model, mundlak = mundlak_model)
}

# ==============================================================================
# 5. REGRESSION SPECIFIC UTILITIES
# ==============================================================================

#' Extract and format regression results
extract_regression_results <- function(model, model_name = "") {
  list(
    coefficients = summary(model)$coefficients,
    r_squared = ifelse("r.squared" %in% names(summary(model)), summary(model)$r.squared, NA),
    n_obs = nobs(model),
    model_name = model_name
  )
}

#' Run complete regression suite
run_regression_suite <- function(df_urban, df_rural) {
  cat("=== BASIC PANEL REGRESSIONS ===\n")
  basic_models <- run_panel_regression(df_urban, df_rural)
  
  cat("\n=== MUNDLAK ESTIMATION ===\n")
  mundlak_urban <- mundlak_estimation(df_urban)
  mundlak_rural <- mundlak_estimation(df_rural)
  stargazer(mundlak_urban, mundlak_rural, type = 'text', column.labels = c("Urban", "Rural"))
  
  cat("\n=== DUMMY VARIABLE ANALYSIS ===\n")
  dummy_urban <- analyze_dummy_effects(df_urban)
  dummy_rural <- analyze_dummy_effects(df_rural)
  
  cat("\n=== INTERACTION ANALYSIS ===\n")
  interact_urban <- analyze_dummy_interactions(df_urban)
  interact_rural <- analyze_dummy_interactions(df_rural)
  
  list(
    basic = basic_models,
    mundlak = list(urban = mundlak_urban, rural = mundlak_rural),
    dummy = list(urban = dummy_urban, rural = dummy_rural),
    interactions = list(urban = interact_urban, rural = interact_rural)
  )
}