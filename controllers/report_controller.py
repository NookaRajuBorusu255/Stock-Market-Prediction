from flask import Blueprint, send_file, flash, redirect, url_for
from flask_login import login_required
from services.report_service import generate_pdf_report

report_bp = Blueprint('report', __name__)

@report_bp.route('/report/download/<symbol>')
@login_required
def download_pdf_report(symbol):
    """
    Generates and downloads a compiled PDF report for a given stock.
    """
    try:
        pdf_buffer = generate_pdf_report(symbol)
        filename = f"{symbol.upper()}_AI_Analysis_Report.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f"Failed to generate report: {str(e)}", "danger")
        return redirect(url_for('dashboard.index'))
