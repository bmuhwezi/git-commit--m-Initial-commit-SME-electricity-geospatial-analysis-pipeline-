#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustering and statistical analysis utilities
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn import cluster, preprocessing
from scipy.optimize import curve_fit
import statsmodels.api as sm


def perform_kmeans_clustering(data, max_clusters=10):
    """
    Perform k-means clustering with different numbers of clusters
    
    Args:
        data (pd.Series or pd.DataFrame): Data to cluster
        max_clusters (int): Maximum number of clusters to try
        
    Returns:
        tuple: (scores, cluster_labels) for different k values
    """
    cluster_range = list(range(1, max_clusters + 1))
    
    # Prepare data
    if isinstance(data, pd.Series):
        features = data.values.reshape(-1, 1)
    elif isinstance(data, pd.DataFrame):
        features = data.iloc[:, 1:].values
    else:
        raise ValueError("Please input pandas DataFrame or Series")
    
    # Initialize results
    scores = pd.Series(index=cluster_range)
    labels = pd.DataFrame(index=data.index, columns=cluster_range)
    
    # Scale features
    features_scaled = preprocessing.scale(features)
    
    # Try different numbers of clusters
    for k in cluster_range:
        kmeans = cluster.KMeans(n_clusters=k, random_state=42)
        cluster_labels = kmeans.fit_predict(features_scaled)
        labels[k] = cluster_labels
        scores[k] = kmeans.score(features_scaled)
    
    return scores, labels


def plot_elbow_curve(scores, labels):
    """
    Plot elbow curve for cluster analysis
    
    Args:
        scores (pd.Series): Clustering scores
        labels (pd.DataFrame): Cluster labels
    """
    sns.set(color_codes=True)
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=labels.columns, y=scores)
    plt.xlabel('Number of Clusters (K)')
    plt.ylabel('Clustering Score')
    plt.title('Elbow Curve for Optimal Cluster Selection')
    plt.show()


def exponential_decay_function(x, a, b, c):
    """
    Exponential decay function for curve fitting
    
    Args:
        x: Input variable
        a, b, c: Function parameters
        
    Returns:
        Exponential decay values
    """
    return a * np.exp(-b * x) + c


def fit_consumption_curve(x_data, y_data, plot_title="Consumption Curve Fit"):
    """
    Fit exponential decay curve to consumption data
    
    Args:
        x_data: Time data (months after connection)
        y_data: Consumption data
        plot_title: Title for the plot
        
    Returns:
        dict: Fitted parameters and R-squared value
    """
    try:
        # Fit exponential decay curve
        popt, pcov = curve_fit(exponential_decay_function, x_data, y_data)
        y_fitted = exponential_decay_function(x_data, *popt)
        
        # Calculate R-squared
        ss_res = np.sum((y_fitted - y_data) ** 2)
        ss_tot = np.sum((y_fitted - np.mean(y_data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        # Plot results
        plt.figure(figsize=(10, 6))
        plt.scatter(x_data, y_data, s=3, alpha=0.6, label='Data')
        plt.scatter(x_data, y_fitted, color='red', s=2, 
                   label=f'Fitted curve (R² = {r_squared:.3f})')
        plt.xlabel('Months after connection')
        plt.ylabel('Consumption')
        plt.title(plot_title)
        plt.legend()
        plt.show()
        
        return {
            'parameters': popt,
            'covariance': pcov,
            'r_squared': r_squared,
            'fitted_values': y_fitted
        }
    
    except Exception as e:
        print(f"Curve fitting failed: {e}")
        return None


def calculate_consumption_statistics_by_customer(billing_data):
    """
    Calculate various consumption statistics by customer
    
    Args:
        billing_data (pd.DataFrame): Billing data
        
    Returns:
        pd.DataFrame: Customer statistics
    """
    customer_stats = pd.DataFrame({
        'Mean': billing_data.groupby('nis_rad').csmo_fact.mean(),
        'Median': billing_data.groupby('nis_rad').csmo_fact.median(),
        'Max': billing_data.groupby('nis_rad').csmo_fact.max(),
        'Min': billing_data.groupby('nis_rad').csmo_fact.min(),
        'Std': billing_data.groupby('nis_rad').csmo_fact.std(),
        'Count': billing_data.groupby('nis_rad').csmo_fact.count()
    })
    
    return customer_stats


def perform_regression_analysis(features, target):
    """
    Perform OLS regression analysis
    
    Args:
        features (pd.DataFrame): Feature matrix
        target (pd.Series): Target variable
        
    Returns:
        statsmodels regression results
    """
    # Add constant term
    features_with_const = sm.add_constant(features)
    
    # Ensure same index order
    features_aligned = features_with_const.reindex(target.index)
    
    # Fit model
    model = sm.OLS(target, features_aligned).fit()
    
    return model


def create_consumption_segments_by_clusters(billing_data, cluster_labels, n_clusters):
    """
    Create consumption segments based on cluster analysis
    
    Args:
        billing_data (pd.DataFrame): Billing data
        cluster_labels (pd.DataFrame): Cluster labels from clustering analysis
        n_clusters (int): Number of clusters to use
        
    Returns:
        dict: Segments with their consumption data
    """
    segments = {}
    clusters = {}
    
    # Get customers for each cluster
    for cluster_id in cluster_labels[n_clusters].unique():
        customer_ids = cluster_labels.index[cluster_labels[n_clusters] == cluster_id].values
        customer_bills = billing_data[billing_data.nis_rad.isin(customer_ids)]
        segments[cluster_id] = customer_bills
    
    # Calculate consumption growth for each segment
    for cluster_id in segments:
        from consumption_analyzer import calculate_consumption_growth
        clusters[f'SC{cluster_id}'] = calculate_consumption_growth(segments[cluster_id])
    
    return clusters


def plot_consumption_by_clusters(cluster_segments):
    """
    Plot consumption curves for different clusters
    
    Args:
        cluster_segments (dict): Dictionary of cluster segments
    """
    sns.set(color_codes=True)
    plt.figure(figsize=(12, 8))
    
    for i, (cluster_name, data) in enumerate(cluster_segments.items()):
        # Filter and sort data
        filtered_data = data[data.Nof_Mths <= 125].copy()
        filtered_data.sort_values('Nof_Mths', inplace=True)
        
        # Plot with fill between quartiles
        plt.fill_between(
            filtered_data.Nof_Mths, 
            filtered_data.Qrtl1, 
            filtered_data.Qrtl3,
            alpha=0.2, 
            label=f'{cluster_name} IQR'
        )
        plt.plot(
            filtered_data.Nof_Mths, 
            filtered_data.Median, 
            label=f'{cluster_name} Median'
        )
    
    plt.xlabel('Number of Months after Connection')
    plt.ylabel('Monthly KWh Consumption')
    plt.title('Consumption Patterns by Customer Segments')
    plt.legend()
    plt.show()


def plot_median_curves_only(cluster_segments):
    """
    Plot only median consumption curves for clusters
    
    Args:
        cluster_segments (dict): Dictionary of cluster segments
    """
    sns.set(color_codes=True)
    plt.figure(figsize=(12, 8))
    
    for i, (cluster_name, data) in enumerate(cluster_segments.items()):
        filtered_data = data[data.Nof_Mths <= 125].copy()
        filtered_data.sort_values('Nof_Mths', inplace=True)
        
        sns.lineplot(
            x=filtered_data.Nof_Mths, 
            y=filtered_data.Median, 
            label=cluster_name
        )
    
    plt.xlabel('Number of Months after Connection')
    plt.ylabel('Monthly KWh Consumption')
    plt.title('Median Consumption by Customer Segments')
    plt.legend()
    plt.show()


def create_cdf_plot(data_series, xlabel="Value"):
    """
    Create cumulative distribution function plot
    
    Args:
        data_series (pd.Series): Data to plot
        xlabel (str): Label for x-axis
    """
    sns.set(color_codes=True)
    
    # Calculate CDF
    sorted_data = data_series.sort_values()
    value_counts = sorted_data.value_counts()
    value_counts.sort_index(inplace=True)
    
    x = value_counts.index
    y = value_counts.cumsum() / len(data_series)
    
    # Plot up to 99th percentile for better visualization
    y_filtered = y[y <= 0.99]
    
    plt.figure(figsize=(10, 6))
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel('Cumulative Probability')
    plt.title(f'Cumulative Distribution of {xlabel}')
    plt.show()


def compare_segment_distributions(data_dict):
    """
    Compare distributions across different segments
    
    Args:
        data_dict (dict): Dictionary with segment names as keys and data as values
    """
    plt.figure(figsize=(12, 8))
    
    for segment_name, data in data_dict.items():
        if hasattr(data, 'values'):
            create_cdf_plot(data, segment_name)
    
    plt.legend()
    plt.title('Distribution Comparison Across Segments')
    plt.show()