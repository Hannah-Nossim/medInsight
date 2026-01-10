from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime


def generate_pdf_report(consultation):
    """
    Generate a PDF report for a consultation
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    # Title
    elements.append(Paragraph("MedInsight Consultation Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Consultation Metadata Table (Replaces Patient Info)
    meta_data = [
        ['Consultation ID:', f"#{consultation.pk}"],
        ['Date:', consultation.created_at.strftime('%B %d, %Y - %I:%M %p')],
        ['Language:', consultation.get_language_display()],
        ['Status:', 'Reviewed' if consultation.is_reviewed else 'Pending Review']
    ]
    
    meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Clinical Case Narrative (The single input field)
    elements.append(Paragraph("Clinical Case Narrative", heading_style))
    # Replace newlines with <br/> for PDF rendering
    case_text = consultation.clinical_case.replace('\n', '<br/>')
    elements.append(Paragraph(case_text, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Page break before AI analysis to keep it clean
    elements.append(PageBreak())
    
    # Clinical Summary
    if consultation.summary:
        elements.append(Paragraph("Clinical Summary", heading_style))
        summary_text = consultation.summary.replace('\n', '<br/>')
        elements.append(Paragraph(summary_text, normal_style))
        elements.append(Spacer(1, 0.2*inch))
    
    # Diagnosis
    if consultation.diagnosis:
        elements.append(Paragraph("Diagnosis", heading_style))
        diagnosis_text = consultation.diagnosis.replace('\n', '<br/>')
        elements.append(Paragraph(diagnosis_text, normal_style))
        elements.append(Spacer(1, 0.2*inch))
    
    # Management
    if consultation.management:
        elements.append(Paragraph("Management Plan", heading_style))
        management_text = consultation.management.replace('\n', '<br/>')
        elements.append(Paragraph(management_text, normal_style))
        elements.append(Spacer(1, 0.2*inch))
    
    # Footer/Disclaimer
    elements.append(Spacer(1, 0.5*inch))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    disclaimer = """
    <b>Clinical Disclaimer:</b> This consultation record was generated with AI assistance. 
    All clinical decisions should be made by qualified healthcare professionals based on their 
    professional judgment, patient assessment, and current clinical guidelines. This tool is 
    designed to support, not replace, clinical expertise.
    """
    elements.append(Paragraph(disclaimer, disclaimer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf