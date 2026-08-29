"""
Optimized DataFrame Utilities
Issue: #1282
Purpose: Optimize data processing for large datasets using vectorized operations.
"""

import pandas as pd


def process_user_data_optimized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimized function to process large user datasets using vectorized operations.
    """
    # Ensure required columns exist
    required_columns = ["user_id", "age", "score", "active"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = 0

    # Vectorized operation: Add 1 to score if active
    df["score"] = df["score"] + df["active"].astype(int)
    
    # Vectorized filtering: Only keep users above 18
    df = df[df["age"] > 18]
    
    # Group by active status and calculate average age
    avg_age = df.groupby("active")["age"].mean().reset_index()
    avg_age.columns = ["active_status", "avg_age"]
    
    return df, avg_age


def calculate_dashboard_metrics_optimized(df: pd.DataFrame) -> dict:
    """
    Optimized function to calculate dashboard metrics.
    """
    total_users = len(df)
    active_users = len(df[df["active"] == True])
    inactive_users = total_users - active_users
    average_score = df["score"].mean() if total_users > 0 else 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "average_score": round(average_score, 2)
    }