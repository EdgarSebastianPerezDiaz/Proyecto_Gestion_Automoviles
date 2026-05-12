"""
PDF generator module - generates freight transport documents using ReportLab.

This module provides functionality to generate various freight transport documents:
- Orden de Cargue (Loading Order)
- Manifiesto de Viaje (Travel Manifest)
- Cumplido (Delivery Confirmation)
- Factura (Invoice)

All PDFs are generated in memory and returned as bytes.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from decimal import Decimal


class PDFGenerationError(Exception):
    """Error during PDF generation."""
    pass


def _format_currency(value: float) -> str:
    """Format value as Colombian peso currency."""
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_date(date_obj: Any) -> str:
    """Format date for display."""
    if isinstance(date_obj, str):
        return date_obj
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%d/%m/%Y %H:%M")
    return str(date_obj)


def generate_orden_cargue(trip_data: Dict[str, Any]) -> bytes:
    """
    Generate "Orden de Cargue" (Loading Order) PDF.
    
    Document includes:
    - Trip identification
    - Origin and destination
    - Vehicle and driver info
    - Cargo weight and type
    - Departure date and notes
    
    Args:
        trip_data: Trip information dictionary containing:
            - _id: Trip ID
            - origin: Origin location
            - destination: Destination location
            - weight_tons: Weight in tons
            - vehicle_id: Vehicle identifier
            - driver_id: Driver identifier
            - cargo_id: Cargo type
            - departure_date: Scheduled departure
            - notes: Additional notes
            
    Returns:
        PDF content as bytes
        
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a4d7a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("ORDEN DE CARGUE", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Document info
        doc_info_data = [
            ["Número de Orden:", str(trip_data.get('_id', 'N/A'))],
            ["Fecha de Creación:", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")],
        ]
        doc_table = Table(doc_info_data, colWidths=[1.5*inch, 4*inch])
        doc_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(doc_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Route information
        route_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1a4d7a'), fontName='Helvetica-Bold')
        story.append(Paragraph("RUTA", route_style))
        
        route_data = [
            ["Origen:", str(trip_data.get('origin', 'N/A'))],
            ["Destino:", str(trip_data.get('destination', 'N/A'))],
            ["Fecha de Salida:", _format_date(trip_data.get('departure_date', 'N/A'))],
        ]
        route_table = Table(route_data, colWidths=[1.5*inch, 4*inch])
        route_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(route_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Cargo information
        story.append(Paragraph("INFORMACIÓN DE CARGA", route_style))
        
        # Handle invalid weight gracefully
        try:
            weight_str = f"{float(trip_data.get('weight_tons', 0)):.2f}"
        except (ValueError, TypeError):
            weight_str = "N/A"
        
        cargo_data = [
            ["Peso (Toneladas):", weight_str],
            ["Tipo de Carga:", str(trip_data.get('cargo_id', 'N/A'))],
        ]
        cargo_table = Table(cargo_data, colWidths=[1.5*inch, 4*inch])
        cargo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(cargo_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Transport information
        story.append(Paragraph("INFORMACIÓN DE TRANSPORTE", route_style))
        
        transport_data = [
            ["ID de Vehículo:", str(trip_data.get('vehicle_id', 'N/A'))],
            ["ID de Conductor:", str(trip_data.get('driver_id', 'N/A'))],
        ]
        transport_table = Table(transport_data, colWidths=[1.5*inch, 4*inch])
        transport_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(transport_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Notes
        notes = trip_data.get('notes', '')
        if notes:
            story.append(Paragraph("NOTAS", route_style))
            story.append(Paragraph(str(notes), styles['Normal']))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        raise PDFGenerationError(f"Error generating Orden de Cargue: {str(e)}")


def generate_manifesto(trip_data: Dict[str, Any]) -> bytes:
    """
    Generate "Manifiesto de Viaje" (Travel Manifest) PDF.
    
    Document includes:
    - Trip manifest header
    - Complete trip details (origin, destination, dates)
    - Cargo and cost information
    - Recipient details
    - Cost breakdown with total
    
    Args:
        trip_data: Trip information dictionary
        
    Returns:
        PDF content as bytes
        
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a4d7a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("MANIFIESTO DE VIAJE", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Trip header
        trip_header = [
            ["ID de Viaje:", str(trip_data.get('_id', 'N/A'))],
            ["Fecha de Creación:", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")],
        ]
        header_table = Table(trip_header, colWidths=[1.5*inch, 4*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Trip details section
        section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1a4d7a'), fontName='Helvetica-Bold')
        story.append(Paragraph("DETALLES DEL VIAJE", section_style))
        
        trip_details = [
            ["Origen:", str(trip_data.get('origin', 'N/A'))],
            ["Destino:", str(trip_data.get('destination', 'N/A'))],
            ["Salida:", _format_date(trip_data.get('departure_date', 'N/A'))],
            ["Llegada:", _format_date(trip_data.get('arrival_date', 'N/A')) if trip_data.get('arrival_date') else "Pendiente"],
            ["Peso (Toneladas):", f"{trip_data.get('weight_tons', 0):.2f}"],
            ["Tipo de Carga:", str(trip_data.get('cargo_id', 'N/A'))],
        ]
        details_table = Table(trip_details, colWidths=[1.5*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Personnel section
        story.append(Paragraph("PERSONAL DEL TRANSPORTE", section_style))
        
        personnel_data = [
            ["ID de Vehículo:", str(trip_data.get('vehicle_id', 'N/A'))],
            ["ID de Conductor:", str(trip_data.get('driver_id', 'N/A'))],
            ["ID de Cliente:", str(trip_data.get('client_id', 'N/A'))],
            ["ID de Destinatario:", str(trip_data.get('recipient_id', 'N/A'))],
        ]
        personnel_table = Table(personnel_data, colWidths=[1.5*inch, 4*inch])
        personnel_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(personnel_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Cost section
        story.append(Paragraph("COSTO DEL VIAJE", section_style))
        
        total_cost = trip_data.get('total_cost', 0)
        cost_data = [
            ["Costo Total:", _format_currency(total_cost)],
        ]
        cost_table = Table(cost_data, colWidths=[1.5*inch, 4*inch])
        cost_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1a4d7a')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f5')),
        ]))
        story.append(cost_table)
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        raise PDFGenerationError(f"Error generating Manifiesto de Viaje: {str(e)}")


def generate_cumplido(trip_data: Dict[str, Any]) -> bytes:
    """
    Generate "Cumplido" (Delivery Confirmation) PDF.
    
    Document includes:
    - Delivery confirmation header
    - Trip and cargo information
    - Recipient signature area
    - Delivery status and date
    - Verification notes
    
    Args:
        trip_data: Trip information dictionary
        
    Returns:
        PDF content as bytes
        
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a4d7a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("CUMPLIDO DE ENTREGA", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Delivery header
        delivery_header = [
            ["ID de Viaje:", str(trip_data.get('_id', 'N/A'))],
            ["Fecha de Entrega:", _format_date(trip_data.get('arrival_date', 'N/A')) if trip_data.get('arrival_date') else datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")],
        ]
        header_table = Table(delivery_header, colWidths=[1.5*inch, 4*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Cargo details
        section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1a4d7a'), fontName='Helvetica-Bold')
        story.append(Paragraph("INFORMACIÓN DE ENTREGA", section_style))
        
        cargo_details = [
            ["Origen:", str(trip_data.get('origin', 'N/A'))],
            ["Destino:", str(trip_data.get('destination', 'N/A'))],
            ["Peso Entregado (Toneladas):", f"{trip_data.get('weight_tons', 0):.2f}"],
            ["ID de Destinatario:", str(trip_data.get('recipient_id', 'N/A'))],
            ["Costo Total:", _format_currency(trip_data.get('total_cost', 0))],
        ]
        cargo_table = Table(cargo_details, colWidths=[1.5*inch, 4*inch])
        cargo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(cargo_table)
        story.append(Spacer(1, 0.25*inch))
        
        # Signature section
        story.append(Paragraph("FIRMA DEL DESTINATARIO", section_style))
        story.append(Spacer(1, 0.1*inch))
        
        sig_data = [["_" * 40], ["Firma y Data del Destinatario"]]
        sig_table = Table(sig_data, colWidths=[5.5*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(sig_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Delivery confirmation
        story.append(Paragraph("ESTADO DE ENTREGA", section_style))
        status_text = "La carga ha sido entregada en perfecto estado al destinatario indicado."
        story.append(Paragraph(status_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        raise PDFGenerationError(f"Error generating Cumplido: {str(e)}")


def generate_invoice(trip_data: Dict[str, Any], invoice_data: Dict[str, Any]) -> bytes:
    """
    Generate Invoice (Factura) PDF.
    
    Document includes:
    - Invoice header with number and dates
    - Trip information
    - Itemized costs and charges
    - Tax calculation (IVA 19%)
    - Total amount due
    - Company and payment information
    
    Args:
        trip_data: Trip information dictionary
        invoice_data: Invoice information dictionary containing:
            - invoice_number: Invoice identifier
            - amount: Base amount before tax
            - tax_amount: Tax amount (IVA)
            - total_amount: Final total
            - issued_at: Invoice issue date
            - due_date: Payment due date
            - status: Invoice status
            
    Returns:
        PDF content as bytes
        
    Raises:
        PDFGenerationError: If PDF generation fails
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Header
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a4d7a'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("FACTURA", title_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Invoice info
        invoice_number = invoice_data.get('invoice_number', 'N/A')
        issue_date = _format_date(invoice_data.get('issued_at', datetime.now(timezone.utc)))
        
        invoice_header = [
            ["Número de Factura:", str(invoice_number), "", "Fecha de Emisión:", issue_date],
            ["ID de Viaje:", str(trip_data.get('_id', 'N/A')), "", "Fecha de Vencimiento:", _format_date(invoice_data.get('due_date', 'N/A'))],
        ]
        header_table = Table(invoice_header, colWidths=[1.2*inch, 1.8*inch, 0.5*inch, 1.5*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Trip & client info section
        section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#1a4d7a'), fontName='Helvetica-Bold')
        story.append(Paragraph("INFORMACIÓN DE LA ENTREGA", section_style))
        
        trip_info = [
            ["Origen:", str(trip_data.get('origin', 'N/A')), "", "Destino:", str(trip_data.get('destination', 'N/A'))],
            ["Peso (Toneladas):", f"{trip_data.get('weight_tons', 0):.2f}", "", "Cliente:", str(trip_data.get('client_id', 'N/A'))],
            ["Tipo de Carga:", str(trip_data.get('cargo_id', 'N/A')), "", "Destinatario:", str(trip_data.get('recipient_id', 'N/A'))],
        ]
        trip_table = Table(trip_info, colWidths=[1.2*inch, 1.8*inch, 0.3*inch, 1.2*inch, 1.8*inch])
        trip_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(trip_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Itemized charges
        story.append(Paragraph("DESGLOSE DE CARGOS", section_style))
        
        base_amount = invoice_data.get('amount', 0)
        tax_amount = invoice_data.get('tax_amount', 0)
        total_amount = invoice_data.get('total_amount', 0)
        
        items_data = [
            ["CONCEPTO", "VALOR"],
            ["Servicio de Transporte", _format_currency(base_amount)],
            ["IVA (19%)", _format_currency(tax_amount)],
            ["TOTAL A PAGAR", _format_currency(total_amount)],
        ]
        
        items_table = Table(items_data, colWidths=[4*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 2), 9),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0f5')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1a4d7a')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.25*inch))
        
        # Invoice status
        status = invoice_data.get('status', 'pending').upper()
        status_text = f"Estado de la Factura: <b>{status}</b>"
        story.append(Paragraph(status_text, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Footer
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        story.append(Paragraph("Gracias por su preferencia", footer_style))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        raise PDFGenerationError(f"Error generating Invoice: {str(e)}")


def upload_to_s3(pdf_bytes: bytes, filename: str) -> str:
    """
    Upload PDF bytes to S3 and return presigned URL.
    
    This is a convenience function that uses the S3Uploader to upload
    PDF content and generate a presigned URL for access.
    
    Args:
        pdf_bytes: PDF content as bytes
        filename: Filename for S3 (without .pdf extension)
        
    Returns:
        Presigned URL for accessing the PDF
        
    Raises:
        PDFGenerationError: If upload fails
    """
    try:
        from src.infrastructure.s3_uploader import get_s3_uploader
        
        uploader = get_s3_uploader()
        key = f"documents/{filename}.pdf"
        
        # Upload PDF
        uploader.upload_pdf(key, pdf_bytes)
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = uploader.generate_presigned_url(key, expiration=3600)
        
        return presigned_url
    
    except Exception as e:
        raise PDFGenerationError(f"Error uploading PDF to S3: {str(e)}")
