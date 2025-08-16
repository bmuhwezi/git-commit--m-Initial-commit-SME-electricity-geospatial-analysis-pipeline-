#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualization utilities for consumption analysis
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from itertools import cycle
from mpl_toolkits.mplot3d import Axes3D
from scipy.optimize import curve_fit


def plot_consumption_by_year(consumption_data):
    """
    Plot consumption growth patterns by year of connection
    
    Args:
        consumption_data (pd.DataFrame): Consumption data with year groupings
    """
    sns.set(color_codes=True)
    fig, axes = plt.subplots(3, 1, figsize=(10, 10))
    
    for year, group in consumption_data.groupby(consumption_data.Year_of_connection):
        y = calculate_consumption_growth(group)
        x = y.nis_rad.groupby(y.Nof_Mths).count()
        Y = y[y.Nof_Mths.isin(x[x >= 500].index.values)]
        
        # Plot median consumption
        sns.lineplot(
            filtered_data.Nof_Mths, 
            filtered_data.Median, 
            ax=axes[0], 
            label=segment_name
        )
        axes[0].set_ylabel('Monthly KWh consumption')
        axes[0].set_xlabel('Number of Months after connection')
        
        # Plot bill counts
        month_counts.sort_index(inplace=True)
        axes[1].plot(month_counts.index, month_counts, '--', 
                    markersize=1, label=segment_name)
        axes[1].set_ylabel('Number of available bills')
        axes[1].set_xlabel('Number of Months after connection')
        axes[1].legend()
    
    plt.tight_layout()
    plt.show()
        sns.lineplot(list(y.Nof_Mths), list(y.Median), ax=axes[0], label=f'{year}')
        axes[0].set_ylabel('Monthly Kwh consumption')
        
        # Plot number of available bills
        axes[1].plot(x.index, x, '--', markersize=3, label=f'{year}')
        axes[1].legend()
        axes[1].set_ylabel('Number of available bills')
        
        # Plot filtered median consumption
        sns.lineplot(list(Y.Nof_Mths), list(Y.Median), ax=axes[2], label=f'{year}')
        axes[2].set_ylabel('Monthly Kwh consumption')
        axes[2].set_xlabel('Number of Months after connection')
    
    plt.tight_layout()
    plt.show()


def plot_consumption_by_classification(classified_data, bills_data):
    """
    Plot consumption patterns by geographic classification
    
    Args:
        classified_data (pd.DataFrame): Data with geographic classifications
        bills_data (pd.DataFrame): Billing data
    """
    for classification, group in classified_data.groupby('classification'):
        if classification != 'NA':
            filtered_bills = bills_data[bills_data.nis_rad.isin(group.NIS_RAD)]
            recent_bills = filtered_bills[filtered_bills.Year_of_connection >= 2009]
            
            plt.figure(figsize=(10, 8))
            plt.suptitle(f'Graph showing {classification} customers')
            plot_consumption_by_year(recent_bills)


def plot_median_consumption_comparison(classified_data, bills_data):
    """
    Plot median consumption comparison across classifications
    
    Args:
        classified_data (pd.DataFrame): Data with geographic classifications
        bills_data (pd.DataFrame): Billing data
    """
    cycol = cycle('bgrcmk')
    plt.figure(figsize=(12, 8))
    
    for classification, group in classified_data.groupby('classification'):
        if classification != 'NA':
            filtered_bills = bills_data[bills_data.nis_rad.isin(group.NIS_RAD)]
            consumption_growth = calculate_consumption_growth(filtered_bills)
            consumption_growth.sort_values('Nof_Mths', inplace=True)
            
            # Filter to reasonable time frame
            filtered_consumption = consumption_growth[consumption_growth.Nof_Mths <= 125]
            
            color = next(cycol)
            plt.plot(
                filtered_consumption.Nof_Mths,
                filtered_consumption.Median,
                color=color,
                linewidth=2,
                label=classification
            )
    
    plt.xlabel('Number of Months after connection')
    plt.ylabel('Monthly KWh consumption')
    plt.legend()
    plt.title('Median Consumption by Geographic Classification')
    plt.show()


def plot_cdf(data_series, label, ax=None):
    """
    Plot cumulative distribution function for a data series
    
    Args:
        data_series (pd.Series): Data to plot CDF for
        label (str): Label for the plot
        ax (matplotlib.axes): Axes object to plot on
    """
    if ax is None:
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
    
    # Calculate CDF
    sorted_data = data_series.sort_values()
    value_counts = sorted_data.value_counts()
    value_counts.sort_index(inplace=True)
    
    x = value_counts.index
    y = value_counts.cumsum() / len(data_series)
    
    # Filter to 99.9th percentile for better visualization
    y_filtered = y[y <= 0.999]
    
    ax.plot(x, y, label=label)
    ax.set_ylabel('Proportion of Service Connections')
    ax.set_xlabel('Value')
    ax.legend()


def plot_cdf_by_group(data_series, group_labels):
    """
    Plot CDFs for different groups
    
    Args:
        data_series (pd.Series): Data to plot
        group_labels (pd.Series): Group labels for each data point
    """
    sns.set(color_codes=True)
    plt.figure(figsize=(12, 8))
    
    for group_name in group_labels.unique():
        if pd.isna(group_name):
            continue
        
        group_data = data_series[group_labels == group_name]
        plot_cdf(group_data, group_name)
    
    plt.title('Cumulative Distribution by Group')
    plt.show()


def plot_feature_scatter(features_df, target_series, feature_cols=None):
    """
    Create scatter plots of features vs target variable
    
    Args:
        features_df (pd.DataFrame): Feature matrix
        target_series (pd.Series): Target variable
        feature_cols (list): Specific columns to plot (if None, plot all numeric)
    """
    if feature_cols is None:
        feature_cols = features_df.select_dtypes(include=[np.number]).columns
    
    n_features = len(feature_cols)
    n_cols = min(3, n_features)
    n_rows = (n_features + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
    if n_rows == 1:
        axes = [axes] if n_cols == 1 else axes
    else:
        axes = axes.flatten()
    
    for i, col in enumerate(feature_cols):
        ax = axes[i] if n_features > 1 else axes
        ax.scatter(features_df[col], target_series, alpha=0.6, s=10)
        ax.set_xlabel(col)
        ax.set_ylabel('Target')
        ax.set_title(f'{col} vs Target')
    
    # Hide unused subplots
    for i in range(len(feature_cols), len(axes)):
        axes[i].set_visible(False)
    
    plt.tight_layout()
    plt.show()


def plot_3d_scatter(x, y, z, labels=None):
    """
    Create 3D scatter plot
    
    Args:
        x, y, z (array-like): Coordinates for 3D plotting
        labels (array-like): Optional labels for coloring points
    """
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    if labels is not None:
        unique_labels = np.unique(labels)
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
        
        for i, label in enumerate(unique_labels):
            mask = labels == label
            ax.scatter(x[mask], y[mask], z[mask], 
                      c=[colors[i]], label=str(label), s=20)
        ax.legend()
    else:
        ax.scatter(x, y, z, s=20)
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.show()


def plot_consumption_segments(bills_data, segments, max_months=125):
    """
    Plot consumption patterns by customer segments
    
    Args:
        bills_data (pd.DataFrame): Billing data
        segments (pd.Series): Customer segment labels
        max_months (int): Maximum months to include in plot
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    for segment_name in segments.unique():
        if pd.isna(segment_name):
            continue
            
        # Get segment customers and their bills
        segment_customers = segments[segments == segment_name]
        segment_bills = bills_data[bills_data.nis_rad.isin(segment_customers.index)]
        
        if len(segment_bills) == 0:
            continue
        
        # Calculate consumption growth
        segment_growth = calculate_consumption_growth(segment_bills)
        
        # Count bills by month
        month_counts = segment_growth.Nof_Mths.value_counts()
        
        # Filter to months with sufficient data and time limit
        valid_months = month_counts[month_counts > 500].index
        filtered_data = segment_growth[
            (segment_growth.Nof_Mths.isin(valid_months)) & 
            (segment_growth.Nof_Mths <= max_months)
        ]
        
        if len(filtered_data) == 0:
            continue
        
        # Plot median consumption