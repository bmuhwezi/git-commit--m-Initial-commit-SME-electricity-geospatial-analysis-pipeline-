#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption analysis utilities for electricity usage patterns
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def calculate_consumption_growth(consumption_data):
    """
    Calculate consumption quartiles and median by months after connection
    
    Args:
        consumption_data (pd.DataFrame): Data with 'Nof_Mths' and 'csmo_fact' columns
        
    Returns:
        pd.DataFrame: Data with added Qrtl1, Qrtl3, and Median columns
    """
    data = consumption_data.copy()
    
    for name, group in data.groupby('Nof_Mths'):
        indices = group.index
        q1 = group.csmo_fact.quantile(q=0.25)
        q3 = group.csmo_fact.quantile(q=0.75)
        median = group.csmo_fact.median()
        
        data.loc[indices, 'Qrtl1'] = q1
        data.loc[indices, 'Qrtl3'] = q3
        data.loc[indices, 'Median'] = median
    
    return data


def analyze_consumption_by_segment(bills_data, segments):
    """
    Analyze consumption patterns for different customer segments
    
    Args:
        bills_data (pd.DataFrame): Billing data
        segments (pd.Series): Customer segment classifications
        
    Returns:
        dict: Analysis results for each segment
    """
    results = {}
    
    for segment_name in segments.unique():
        if pd.isna(segment_name):
            continue
            
        # Get customers in this segment
        segment_customers = segments[segments == segment_name]
        segment_bills = bills_data[bills_data.nis_rad.isin(segment_customers.index)]
        
        if len(segment_bills) == 0:
            continue
        
        # Calculate growth metrics
        segment_growth = calculate_consumption_growth(segment_bills)
        
        # Aggregate statistics
        results[segment_name] = {
            'data': segment_growth,
            'customer_count': len(segment_customers),
            'bill_count': len(segment_bills),
            'avg_consumption': segment_bills.csmo_fact.mean(),
            'median_consumption': segment_bills.csmo_fact.median()
        }
    
    return results


def create_consumption_summary(bills_data, group_by_col='nis_rad'):
    """
    Create summary statistics for consumption by customer
    
    Args:
        bills_data (pd.DataFrame): Billing data
        group_by_col (str): Column to group by
        
    Returns:
        pd.DataFrame: Summary statistics
    """
    summary = pd.DataFrame({
        'Mean_Kwh': bills_data.groupby(group_by_col).csmo_fact.mean(),
        'Median_Kwh': bills_data.groupby(group_by_col).csmo_fact.median(),
        'Std_Kwh': bills_data.groupby(group_by_col).csmo_fact.std(),
        'Count': bills_data.groupby(group_by_col).csmo_fact.count()
    })
    
    return summary


def segment_customers_by_consumption(consumption_summary, percentiles=[0.33, 0.67]):
    """
    Segment customers into consumption tiers based on percentiles
    
    Args:
        consumption_summary (pd.DataFrame): Customer consumption summary
        percentiles (list): Percentile cutoffs for segmentation
        
    Returns:
        pd.Series: Customer segments (Low, Medium, High)
    """
    mean_consumption = consumption_summary['Mean_Kwh']
    cutoffs = mean_consumption.quantile(percentiles)
    
    segments = pd.Series(index=mean_consumption.index, dtype='object')
    segments[mean_consumption <= cutoffs.iloc[0]] = 'Low'
    segments[(mean_consumption > cutoffs.iloc[0]) & (mean_consumption <= cutoffs.iloc[1])] = 'Medium'
    segments[mean_consumption > cutoffs.iloc[1]] = 'High'
    
    return segments
