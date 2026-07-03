import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to prevent GUI thread blocks
import matplotlib.pyplot as plt
import seaborn as sns

def generate_correlation_heatmap(df, theme='dark'):
    """
    Computes statistical correlations of technical indicators using pandas & numpy.
    Generates a theme-tailored visualization using seaborn & matplotlib and returns it
    as a base64 encoded PNG string.
    """
    # Select columns to calculate correlations
    cols = ['Close', 'SMA_20', 'SMA_50', 'MACD', 'RSI', 'Volatility', 'Volume']
    available_cols = [c for c in cols if c in df.columns]
    
    if not available_cols:
        raise ValueError("No matching technical indicators found for correlation matrix.")
        
    corr = df[available_cols].corr()
    
    # Establish theme-specific colors
    theme_colors = {
        'dark': {
            'bg': '#0d1221',
            'text': '#f8fafc',
            'cmap': 'viridis'
        },
        'light': {
            'bg': '#ffffff',
            'text': '#0f172a',
            'cmap': 'coolwarm'
        },
        'cyberpunk': {
            'bg': '#030008',
            'text': '#00ffff',
            'cmap': 'magma'
        },
        'forest': {
            'bg': '#050d0a',
            'text': '#ecfdf5',
            'cmap': 'YlGnBu'
        }
    }
    
    theme_cfg = theme_colors.get(theme, theme_colors['dark'])
    
    # Configure Matplotlib styles
    plt.rcParams['text.color'] = theme_cfg['text']
    plt.rcParams['axes.labelcolor'] = theme_cfg['text']
    plt.rcParams['xtick.color'] = theme_cfg['text']
    plt.rcParams['ytick.color'] = theme_cfg['text']
    
    # Render figure
    fig, ax = plt.subplots(figsize=(6, 4.5), facecolor=theme_cfg['bg'])
    ax.set_facecolor(theme_cfg['bg'])
    
    # Draw correlation heatmap
    sns.heatmap(
        corr, 
        annot=True, 
        cmap=theme_cfg['cmap'], 
        fmt=".2f", 
        linewidths=0.5, 
        linecolor='#1e293b' if theme != 'light' else '#cbd5e1',
        cbar=True,
        ax=ax,
        annot_kws={"size": 9, "weight": "bold"}
    )
    
    plt.title('Technical Indicator Correlation Matrix', fontsize=11, fontweight='bold', pad=12, color=theme_cfg['text'])
    plt.tight_layout()
    
    # Write output to base64 buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=110, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    
    return base64.b64encode(buf.getvalue()).decode('utf-8')
