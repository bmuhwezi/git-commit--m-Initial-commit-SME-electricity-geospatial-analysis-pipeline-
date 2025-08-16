# ==============================================================================
# VISUALIZATION FUNCTIONS MODULE
# Compact plotting functions for electricity consumption analysis
# ==============================================================================

pacman::p_load(ggplot2, ggthemes, cowplot, dplyr, tidyr, scales, viridis, zoo)

# ==============================================================================
# 1. TIME SERIES PLOTS
# ==============================================================================

#' Plot median consumption over time
plot_median_consumption <- function(df, max_months = 120, show_ribbon = TRUE) {
  plot_data <- df %>%
    filter(Nof_Mths < max_months) %>%
    group_by(Nof_Mths) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE),
              Q1 = quantile(csmo_fact, 0.25, na.rm = TRUE),
              Q3 = quantile(csmo_fact, 0.75, na.rm = TRUE), .groups = 'drop')
  
  p <- ggplot(plot_data, aes(Nof_Mths))
  if (show_ribbon) p <- p + geom_ribbon(aes(ymin = Q1, ymax = Q3), alpha = 0.3, fill = 'lightblue')
  
  p + geom_line(aes(y = med), color = 'blue', size = 1) +
    labs(y = 'Monthly kWh', x = 'Months Since Connection') + theme_minimal()
}

#' Plot median consumption by rural/urban
plot_median_by_location <- function(df, max_months = 120, colors = c("Rural" = "#E74C3C", "Urban" = "#3498DB")) {
  df %>%
    filter(Nof_Mths < max_months) %>%
    group_by(rural_urban, Nof_Mths) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE), .groups = 'drop') %>%
    ggplot(aes(Nof_Mths, med, color = rural_urban)) +
    geom_line(size = 1.2) + scale_color_manual(values = colors) +
    labs(y = 'Monthly kWh', x = 'Months Since Connection', color = 'Location') + theme_minimal()
}

#' Plot consumption by year of connection
plot_consumption_by_year <- function(df, min_year = 2009, min_count = 1200, max_months = 120) {
  plot_data <- df %>%
    filter(Nof_Mths < max_months) %>%
    group_by(Nof_Mths, Year_of_connection) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE), count = n(), .groups = 'drop') %>%
    filter(Year_of_connection >= min_year, count > min_count)
  
  p1 <- ggplot(plot_data, aes(Nof_Mths, med, color = factor(Year_of_connection))) +
    geom_line(size = 1) + scale_color_viridis_d() +
    labs(y = 'Monthly kWh', x = 'Months Since Connection', color = 'Year') + theme_minimal()
  
  p2 <- ggplot(plot_data, aes(Nof_Mths, count, color = factor(Year_of_connection))) +
    geom_line(linetype = "dashed") + scale_color_viridis_d() +
    labs(y = 'Observations', x = 'Months Since Connection', color = 'Year') + theme_minimal()
  
  list(consumption = p1, count = p2)
}

#' Plot seasonal consumption patterns
plot_consumption_calendar <- function(df, ylim_max = 250) {
  df %>%
    group_by(Month) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE),
              Q1 = quantile(csmo_fact, 0.25, na.rm = TRUE),
              Q3 = quantile(csmo_fact, 0.75, na.rm = TRUE), .groups = 'drop') %>%
    mutate(Month = as.yearmon(Month)) %>%
    ggplot(aes(Month)) +
    geom_ribbon(aes(ymin = Q1, ymax = Q3), alpha = 0.3, fill = 'lightblue') +
    geom_line(aes(y = med), color = 'blue', size = 1) +
    labs(y = 'Monthly kWh', x = 'Date') + ylim(0, ylim_max) + theme_minimal()
}

# ==============================================================================
# 2. DISTRIBUTION PLOTS
# ==============================================================================

#' Plot cumulative distributions by rural/urban
plot_cumulative_distributions <- function(df, variables = c('total_structs', 'population', 'fsp', 'min_dist2_road', 'Electrification', 'Night_Lights'), ncol = 3) {
  plot_data <- df %>%
    group_by(nis_rad) %>%
    summarise(across(all_of(variables), ~ mean(.x, na.rm = TRUE)),
              rural_urban = first(rural_urban), .groups = 'drop')
  
  plots <- map(variables, ~{
    p <- ggplot(plot_data, aes_string(.x)) +
      stat_ecdf(aes(color = rural_urban), geom = "step", size = 1) +
      labs(y = 'Proportion', x = str_replace_all(.x, '_', ' ') %>% str_to_title()) +
      scale_color_manual(values = c("Rural" = "#E74C3C", "Urban" = "#3498DB")) +
      theme_light() + theme(legend.position = "none", text = element_text(size = 9))
    
    if (.x %in% c('population', 'fsp', 'total_structs')) p <- p + scale_x_log10()
    p
  })
  
  plots[[1]] <- plots[[1]] + theme(legend.position = c(0.7, 0.3), legend.title = element_blank())
  plot_grid(plotlist = plots, ncol = ncol)
}

#' Plot distribution histograms
plot_distribution_histograms <- function(df, variables = c('csmo_fact', 'total_structs', 'population', 'fsp'), ncol = 2) {
  plots <- map(variables, ~{
    ggplot(df, aes_string(.x, fill = 'rural_urban')) +
      geom_histogram(alpha = 0.7, position = 'identity', bins = 30) +
      labs(x = str_to_title(.x), y = 'Frequency', fill = 'Location') +
      scale_fill_manual(values = c("Rural" = "#E74C3C", "Urban" = "#3498DB")) + theme_minimal()
  })
  plot_grid(plotlist = plots, ncol = ncol)
}

# ==============================================================================
# 3. SEGMENT ANALYSIS PLOTS
# ==============================================================================

#' Plot consumption segments by dummy variable
plot_consumption_segments <- function(df, dummy_var, location = NULL, max_months = 120) {
  if (!is.null(location)) df <- filter(df, rural_urban == location)
  
  plot_data <- df %>%
    filter(Nof_Mths < max_months) %>%
    group_by_at(vars(all_of(dummy_var), 'Nof_Mths')) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE), count = n(), .groups = 'drop')
  
  p1 <- ggplot(plot_data, aes(Nof_Mths, count)) +
    geom_line(aes_string(color = dummy_var), linetype = "dashed") +
    labs(y = 'Observations', color = str_to_title(dummy_var)) + theme_minimal()
  
  p2 <- ggplot(plot_data, aes(Nof_Mths, med)) +
    geom_line(aes_string(color = dummy_var), size = 1) +
    labs(y = 'Monthly kWh', x = 'Months Since Connection', color = str_to_title(dummy_var)) + theme_minimal()
  
  plot_grid(p1, p2, ncol = 1)
}

#' Plot segments with separate rural/urban panels
plot_segments_separate_panels <- function(df, dummy_var, max_months = 120) {
  create_plot <- function(data, title) {
    data %>%
      filter(Nof_Mths < max_months) %>%
      group_by_at(vars(all_of(dummy_var), 'Nof_Mths')) %>%
      summarise(med = median(csmo_fact, na.rm = TRUE), .groups = 'drop') %>%
      ggplot(aes(Nof_Mths, med)) +
      geom_line(aes_string(color = dummy_var), size = 1.2) +
      labs(y = 'Monthly kWh', x = 'Months Since Connection', title = title) +
      theme_minimal() + theme(legend.position = c(0.7, 0.2))
  }
  
  list(rural = create_plot(filter(df, rural_urban == 'Rural'), "Rural"),
       urban = create_plot(filter(df, rural_urban == 'Urban'), "Urban"))
}

# ==============================================================================
# 4. INTERACTION PLOTS
# ==============================================================================

#' Create combined dummy variable
create_combined_dummy <- function(df, dummy1, dummy2) {
  str1 <- strsplit(dummy1, '_')[[1]][1]
  str2 <- strsplit(dummy2, '_')[[1]][1]
  
  df$dummy_comb <- case_when(
    df[[dummy1]] == "Low" & df[[dummy2]] == "Low" ~ paste0("Low_", str1, "_Low_", str2),
    df[[dummy1]] == "Low" & df[[dummy2]] == "High" ~ paste0("Low_", str1, "_High_", str2),
    df[[dummy1]] == "High" & df[[dummy2]] == "Low" ~ paste0("High_", str1, "_Low_", str2),
    df[[dummy1]] == "High" & df[[dummy2]] == "High" ~ paste0("High_", str1, "_High_", str2)
  )
  df$dummy_comb <- as.factor(df$dummy_comb)
  df
}

#' Plot dummy variable interactions
plot_dummy_interactions <- function(df, dummy1, dummy2, location = NULL, max_months = 120) {
  if (!is.null(location)) df <- filter(df, rural_urban == location)
  
  df <- create_combined_dummy(df, dummy1, dummy2)
  
  df %>%
    filter(Nof_Mths < max_months) %>%
    group_by(dummy_comb, Nof_Mths) %>%
    summarise(med = median(csmo_fact, na.rm = TRUE), .groups = 'drop') %>%
    ggplot(aes(Nof_Mths, med, color = dummy_comb)) +
    geom_line(size = 1) +
    labs(y = 'Monthly kWh', x = 'Months Since Connection', color = 'Interaction') +
    theme_minimal() + theme(legend.position = 'right')
}

#' Plot all pairwise interactions
plot_all_interactions <- function(df, dummy_vars = c("fsp_dummy", "Electrification_dummy", "population_dummy", "dist2_road_dummy", "structs_dummy", "NL_dummy"), output_dir = NULL) {
  plots <- list()
  n <- length(dummy_vars)
  
  for (i in 1:(n-1)) {
    for (j in (i+1):n) {
      rural_plot <- plot_dummy_interactions(df, dummy_vars[i], dummy_vars[j], "Rural")
      urban_plot <- plot_dummy_interactions(df, dummy_vars[i], dummy_vars[j], "Urban")
      combined <- plot_grid(rural_plot, urban_plot, ncol = 1, labels = c("Rural", "Urban"))
      
      plot_name <- paste(gsub("_dummy", "", dummy_vars[i]), gsub("_dummy", "", dummy_vars[j]), sep = "_")
      plots[[plot_name]] <- combined
      
      if (!is.null(output_dir)) {
        ggsave(file.path(output_dir, paste0(plot_name, "_interaction.png")), combined, width = 12, height = 8)
      }
    }
  }
  plots
}