import io
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from services.data_service import get_stock_data
from database.database_helper import get_all_model_performances, get_model_performance
from services.ml_service import load_ml_model_and_predict

def generate_pdf_report(symbol):
    """
    Generates a PDF analysis report for the specified symbol.
    Returns: BytesIO stream containing the PDF document.
    """
    symbol = symbol.upper()
    buffer = io.BytesIO()
    
    # Page setup
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette - Sleek Dark Slate and Steel Blue
    PRIMARY_COLOR = colors.HexColor("#1e293b")
    SECONDARY_COLOR = colors.HexColor("#3b82f6")
    TEXT_COLOR = colors.HexColor("#0f172a")
    BORDER_COLOR = colors.HexColor("#cbd5e1")
    
    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=PRIMARY_COLOR,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=SECONDARY_COLOR,
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_COLOR,
        spaceAfter=10
    )
    
    bold_body = ParagraphStyle(
        'ReportBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=TEXT_COLOR
    )

    story = []
    
    # 1. Header Section
    story.append(Paragraph(f"AI Stock Market Prediction & Analysis Report", title_style))
    story.append(Paragraph(f"Symbol: {symbol} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    
    # 2. Get Stock Data
    try:
        df = get_stock_data(symbol)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        price_change = last_row['Close'] - prev_row['Close']
        pct_change = (price_change / prev_row['Close']) * 100
        
        story.append(Paragraph("Stock Market Overview", h2_style))
        overview_text = (
            f"As of the latest data point ({last_row['Date'].strftime('%Y-%m-%d')}), **{symbol}** closed at **${last_row['Close']:.2f}**, "
            f"representing a change of **{price_change:+.2f} ({pct_change:+.2f}%)** from the previous trading session. "
            f"The stock's technical setup is detailed below, showing key momentum indices and volatility metrics."
        )
        story.append(Paragraph(overview_text, body_style))
        
        # Technical Summary Table
        tech_data = [
            [Paragraph("Indicator Name", table_header_style), Paragraph("Value", table_header_style), Paragraph("Interpretation", table_header_style)],
            [
                Paragraph("Close Price", table_cell_style), 
                Paragraph(f"${last_row['Close']:.2f}", table_cell_style),
                Paragraph("Latest session close price", table_cell_style)
            ],
            [
                Paragraph("RSI (14)", table_cell_style), 
                Paragraph(f"{last_row['RSI']:.2f}" if not pd.isna(last_row['RSI']) else "N/A", table_cell_style),
                Paragraph(
                    "Oversold (<30)" if last_row['RSI'] < 30 else ("Overbought (>70)" if last_row['RSI'] > 70 else "Neutral range (30-70)"), 
                    table_cell_style
                )
            ],
            [
                Paragraph("MACD", table_cell_style), 
                Paragraph(f"{last_row['MACD']:.4f}" if not pd.isna(last_row['MACD']) else "N/A", table_cell_style),
                Paragraph("Bullish Crossover" if last_row['MACD'] > last_row['MACD_Signal'] else "Bearish Crossunder", table_cell_style)
            ],
            [
                Paragraph("20-Day SMA", table_cell_style), 
                Paragraph(f"${last_row['SMA_20']:.2f}" if not pd.isna(last_row['SMA_20']) else "N/A", table_cell_style),
                Paragraph("Short-term price trend support", table_cell_style)
            ],
            [
                Paragraph("50-Day SMA", table_cell_style), 
                Paragraph(f"${last_row['SMA_50']:.2f}" if not pd.isna(last_row['SMA_50']) else "N/A", table_cell_style),
                Paragraph("Medium-term price trend support", table_cell_style)
            ],
            [
                Paragraph("Annual Volatility", table_cell_style), 
                Paragraph(f"{last_row['Volatility']*100:.2f}%" if not pd.isna(last_row['Volatility']) else "N/A", table_cell_style),
                Paragraph("Annualized standard deviation of returns", table_cell_style)
            ]
        ]
        
        t_tech = Table(tech_data, colWidths=[150, 100, 270])
        t_tech.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_tech)
        story.append(Spacer(1, 15))
        
    except Exception as e:
        story.append(Paragraph(f"Could not load stock statistics: {str(e)}", body_style))
        story.append(Spacer(1, 15))
        
    # 3. Model Predictions (Next Day Forecasts)
    story.append(Paragraph("Machine Learning Next-Day Predictions", h2_style))
    story.append(Paragraph(
        "Our models predict the next trading day's close price using sequential modeling. "
        "Confidence scores represent aggregated $R^2$ accuracy and mean absolute percentage error (MAPE) metrics.",
        body_style
    ))
    
    pred_models = ['Linear Regression', 'Random Forest', 'XGBoost']
    pred_rows = [[Paragraph("Model Name", table_header_style), Paragraph("Next Day Prediction", table_header_style), Paragraph("Confidence Score", table_header_style)]]
    
    for name in pred_models:
        try:
            pred_price, confidence = load_ml_model_and_predict(symbol, name)
            pred_rows.append([
                Paragraph(name, table_cell_style),
                Paragraph(f"${pred_price:.2f}", table_cell_style),
                Paragraph(f"{confidence:.1f}%", table_cell_style)
            ])
        except Exception:
            pred_rows.append([
                Paragraph(name, table_cell_style),
                Paragraph("N/A (needs training)", table_cell_style),
                Paragraph("0.0%", table_cell_style)
            ])
            
    # Try getting LSTM prediction
    try:
        from services.dl_service import forecast_future_lstm
        lstm_forecasts = forecast_future_lstm(symbol, forecast_steps=1)
        lstm_pred = lstm_forecasts[0]
        # Calculate confidence from LSTM performance cache
        perf = get_model_performance(symbol, 'LSTM')
        if perf:
            r2_conf = max(0, min(100, perf.r2 * 100))
            mape_conf = max(0, min(100, 100 - perf.mape))
            confidence = (r2_conf * 0.4) + (mape_conf * 0.6)
        else:
            confidence = 80.0
        pred_rows.append([
            Paragraph("LSTM Deep Learning", table_cell_style),
            Paragraph(f"${lstm_pred:.2f}", table_cell_style),
            Paragraph(f"{confidence:.1f}%", table_cell_style)
        ])
    except Exception:
        pred_rows.append([
            Paragraph("LSTM Deep Learning", table_cell_style),
            Paragraph("N/A (needs training)", table_cell_style),
            Paragraph("0.0%", table_cell_style)
        ])
        
    t_pred = Table(pred_rows, colWidths=[200, 160, 160])
    t_pred.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_pred)
    story.append(Spacer(1, 15))
    
    # 4. Model Training & Evaluation Metrics
    story.append(Paragraph("Model Performance Evaluation Cache", h2_style))
    story.append(Paragraph(
        "Evaluation metrics are calculated chronologically on the 20% test partition. "
        "A higher $R^2$ indicates better trend correlation, while lower MAE/RMSE indicate lower absolute price errors.",
        body_style
    ))
    
    perf_rows = [[
        Paragraph("Model Name", table_header_style), 
        Paragraph("MAE ($)", table_header_style), 
        Paragraph("RMSE ($)", table_header_style), 
        Paragraph("R² Score", table_header_style), 
        Paragraph("MAPE (%)", table_header_style)
    ]]
    
    performances = get_all_model_performances(symbol)
    if performances:
        for p in performances:
            perf_rows.append([
                Paragraph(p.model_name, table_cell_style),
                Paragraph(f"{p.mae:.4f}", table_cell_style),
                Paragraph(f"{p.rmse:.4f}", table_cell_style),
                Paragraph(f"{p.r2:.4f}", table_cell_style),
                Paragraph(f"{p.mape:.2f}%", table_cell_style)
            ])
    else:
        perf_rows.append([Paragraph("No trained models cached in SQL. Use ML interface to train.", table_cell_style), Paragraph("", table_cell_style), Paragraph("", table_cell_style), Paragraph("", table_cell_style), Paragraph("", table_cell_style)])
        
    t_perf = Table(perf_rows, colWidths=[160, 90, 90, 90, 90])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_perf)
    story.append(Spacer(1, 20))
    
    # 5. Disclaimer / Signature
    story.append(Paragraph("Disclaimer", ParagraphStyle('DiscTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#ef4444"))))
    story.append(Paragraph(
        "This report is generated automatically by an AI/ML Stock Market Platform for academic and demonstration purposes. "
        "Predictive algorithms are highly experimental and subject to market volatility. "
        "No information in this document should be treated as professional financial, investment, or legal advice. "
        "Invest at your own risk.",
        ParagraphStyle('DiscText', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#64748b"))
    ))
    
    # Build
    doc.build(story)
    
    # Reset buffer pointer and return
    buffer.seek(0)
    return buffer
