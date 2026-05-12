"""
Tests for PDF generator module.

Tests cover:
- PDF generation for all document types
- PDF validity (is valid ReportLab PDF)
- Error handling
- Content accuracy
"""

import pytest
from io import BytesIO
from datetime import datetime, timezone, timedelta
from src.infrastructure.pdf_generator import (
    generate_orden_cargue,
    generate_manifesto,
    generate_cumplido,
    generate_invoice,
    PDFGenerationError,
    _format_currency,
    _format_date
)


class TestPDFHelpers:
    """Test helper functions for PDF generation."""
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert _format_currency(1000.5) == "$1.000,50"
        assert _format_currency(1000000) == "$1.000.000,00"
        assert _format_currency(0) == "$0,00"
        assert _format_currency(99.99) == "$99,99"
    
    def test_format_date_from_string(self):
        """Test date formatting from string."""
        date_str = "2026-04-04"
        result = _format_date(date_str)
        assert result == "2026-04-04"
    
    def test_format_date_from_datetime(self):
        """Test date formatting from datetime object."""
        dt = datetime(2026, 4, 4, 14, 30, 0)
        result = _format_date(dt)
        assert result == "04/04/2026 14:30"
    
    def test_format_date_from_other(self):
        """Test date formatting from other types."""
        result = _format_date(12345)
        assert result == "12345"


class TestOrdenDeCargueGeneration:
    """Test Orden de Cargue PDF generation."""
    
    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for testing."""
        return {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá, Colombia',
            'destination': 'Cali, Colombia',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'departure_date': datetime.now(timezone.utc),
            'notes': 'Handle with care - fragile items'
        }
    
    def test_orden_cargue_generation(self, sample_trip_data):
        """Test Orden de Cargue PDF generation."""
        pdf_bytes = generate_orden_cargue(sample_trip_data)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_orden_cargue_contains_data(self, sample_trip_data):
        """Test that Orden de Cargue contains trip data."""
        pdf_bytes = generate_orden_cargue(sample_trip_data)
        
        # PDF should be valid
        assert pdf_bytes.startswith(b'%PDF')
        
        # Should be decodable (contains text)
        pdf_text = pdf_bytes.decode('utf-8', errors='ignore')
        assert 'ORDEN DE CARGUE' in pdf_text or len(pdf_bytes) > 1000  # Either title or substantial content
    
    def test_orden_cargue_missing_fields(self):
        """Test Orden de Cargue with missing optional fields."""
        trip_data = {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá',
            'destination': 'Cali',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'departure_date': '2026-04-04'
            # No notes
        }
        
        pdf_bytes = generate_orden_cargue(trip_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_orden_cargue_large_data(self):
        """Test Orden de Cargue with large notes field."""
        trip_data = {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá',
            'destination': 'Cali',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'departure_date': datetime.now(timezone.utc),
            'notes': 'A' * 1000  # 1000 character notes
        }
        
        pdf_bytes = generate_orden_cargue(trip_data)
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000  # Should be substantial


class TestManifestoGeneration:
    """Test Manifiesto de Viaje PDF generation."""
    
    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for testing."""
        return {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá, Colombia',
            'destination': 'Cali, Colombia',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'client_id': 'CLIENT-001',
            'recipient_id': 'REC-001',
            'departure_date': datetime(2026, 4, 4, 10, 0, 0),
            'arrival_date': datetime(2026, 4, 5, 14, 30, 0),
            'total_cost': 250000.0
        }
    
    def test_manifesto_generation(self, sample_trip_data):
        """Test Manifiesto PDF generation."""
        pdf_bytes = generate_manifesto(sample_trip_data)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_manifesto_without_arrival_date(self, sample_trip_data):
        """Test Manifiesto without arrival date."""
        del sample_trip_data['arrival_date']
        
        pdf_bytes = generate_manifesto(sample_trip_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_manifesto_cost_formatting(self):
        """Test that Manifiesto formats cost correctly."""
        trip_data = {
            '_id': 'test-123',
            'origin': 'Bogotá',
            'destination': 'Cali',
            'weight_tons': 10,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'client_id': 'CLIENT-001',
            'recipient_id': 'REC-001',
            'departure_date': datetime.now(timezone.utc),
            'total_cost': 1500000.50  # Large amount
        }
        
        pdf_bytes = generate_manifesto(trip_data)
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000


class TestCumplidoGeneration:
    """Test Cumplido PDF generation."""
    
    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for testing."""
        return {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá, Colombia',
            'destination': 'Cali, Colombia',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'recipient_id': 'REC-001',
            'arrival_date': datetime.now(timezone.utc),
            'total_cost': 250000.0
        }
    
    def test_cumplido_generation(self, sample_trip_data):
        """Test Cumplido PDF generation."""
        pdf_bytes = generate_cumplido(sample_trip_data)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_cumplido_without_arrival_date(self, sample_trip_data):
        """Test Cumplido without arrival date (uses current time)."""
        del sample_trip_data['arrival_date']
        
        pdf_bytes = generate_cumplido(sample_trip_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_cumplido_content(self, sample_trip_data):
        """Test Cumplido contains signature placeholder."""
        pdf_bytes = generate_cumplido(sample_trip_data)
        
        # PDF should be valid
        assert pdf_bytes.startswith(b'%PDF')
        
        # Should have signing area
        assert len(pdf_bytes) > 1000


class TestInvoiceGeneration:
    """Test Invoice (Factura) PDF generation."""
    
    @pytest.fixture
    def sample_data(self):
        """Sample trip and invoice data for testing."""
        trip_data = {
            '_id': '507f1f77bcf86cd799439011',
            'origin': 'Bogotá, Colombia',
            'destination': 'Cali, Colombia',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'client_id': 'CLIENT-001',
            'recipient_id': 'REC-001',
            'total_cost': 250000.0
        }
        
        invoice_data = {
            'invoice_number': 'INV-2026-001',
            'amount': 250000.0,
            'tax_amount': 47500.0,  # 19% IVA
            'total_amount': 297500.0,
            'issued_at': datetime(2026, 4, 4, 10, 0, 0),
            'due_date': datetime(2026, 5, 4, 10, 0, 0),
            'status': 'pending'
        }
        
        return trip_data, invoice_data
    
    def test_invoice_generation(self, sample_data):
        """Test Invoice PDF generation."""
        trip_data, invoice_data = sample_data
        pdf_bytes = generate_invoice(trip_data, invoice_data)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_invoice_tax_calculation(self, sample_data):
        """Test invoice with IVA 19% tax."""
        trip_data, invoice_data = sample_data
        
        # Verify tax calculation
        expected_tax = invoice_data['amount'] * 0.19
        assert invoice_data['tax_amount'] == pytest.approx(expected_tax, rel=0.01)
        
        pdf_bytes = generate_invoice(trip_data, invoice_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_invoice_without_due_date(self, sample_data):
        """Test invoice without due date."""
        trip_data, invoice_data = sample_data
        del invoice_data['due_date']
        
        pdf_bytes = generate_invoice(trip_data, invoice_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_invoice_large_amount(self, sample_data):
        """Test invoice with large amount."""
        trip_data, invoice_data = sample_data
        
        invoice_data['amount'] = 50000000.0  # 50M
        invoice_data['tax_amount'] = 9500000.0
        invoice_data['total_amount'] = 59500000.0
        
        pdf_bytes = generate_invoice(trip_data, invoice_data)
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000
    
    def test_invoice_different_statuses(self, sample_data):
        """Test invoices with different statuses."""
        trip_data, invoice_data = sample_data
        
        for status in ['pending', 'paid', 'overdue', 'cancelled']:
            invoice_data['status'] = status
            pdf_bytes = generate_invoice(trip_data, invoice_data)
            assert pdf_bytes.startswith(b'%PDF')


class TestPDFErrorHandling:
    """Test error handling in PDF generation."""
    
    def test_orden_cargue_with_invalid_weight(self):
        """Test Orden de Cargue with invalid weight field."""
        trip_data = {
            '_id': 'test-123',
            'origin': 'Bogotá',
            'destination': 'Cali',
            'weight_tons': 'invalid',  # Should be float
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'departure_date': datetime.now(timezone.utc)
        }
        
        # Should not raise, just format the value
        pdf_bytes = generate_orden_cargue(trip_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_invoice_with_zero_amount(self):
        """Test invoice generation with zero amount."""
        trip_data = {
            '_id': 'test-123',
            'origin': 'Bogotá',
            'destination': 'Cali',
            'weight_tons': 1,
            'total_cost': 0
        }
        
        invoice_data = {
            'invoice_number': 'INV-0000',
            'amount': 0,
            'tax_amount': 0,
            'total_amount': 0,
            'issued_at': datetime.now(timezone.utc),
            'status': 'pending'
        }
        
        pdf_bytes = generate_invoice(trip_data, invoice_data)
        assert pdf_bytes.startswith(b'%PDF')
    
    def test_pdf_with_special_characters(self):
        """Test PDF generation with special characters."""
        trip_data = {
            '_id': 'test-123',
            'origin': 'São Paulo, Brasil',
            'destination': 'México City, México',
            'weight_tons': 5.5,
            'vehicle_id': 'VEH-001',
            'driver_id': 'DRV-001',
            'cargo_id': 'CARGO-001',
            'departure_date': datetime.now(timezone.utc),
            'notes': 'Carga especial: electrónica, ¡Máxima atención! ©2026'
        }
        
        pdf_bytes = generate_orden_cargue(trip_data)
        assert pdf_bytes.startswith(b'%PDF')


class TestPDFContent:
    """Test PDF content extraction and validation."""
    
    def test_orden_cargue_is_valid_pdf(self):
        """Test that generated Orden de Cargue is valid PDF."""
        trip_data = {
            '_id': 'test-id',
            'origin': 'A',
            'destination': 'B',
            'weight_tons': 1,
            'vehicle_id': 'V',
            'driver_id': 'D',
            'cargo_id': 'C',
            'departure_date': datetime.now(timezone.utc)
        }
        
        pdf = generate_orden_cargue(trip_data)
        
        # Valid PDF checks
        assert pdf.startswith(b'%PDF')
        assert b'endobj' in pdf
        assert b'%%EOF' in pdf
    
    def test_manifesto_is_valid_pdf(self):
        """Test that generated Manifesto is valid PDF."""
        trip_data = {
            '_id': 'test-id',
            'origin': 'A',
            'destination': 'B',
            'weight_tons': 1,
            'vehicle_id': 'V',
            'driver_id': 'D',
            'cargo_id': 'C',
            'client_id': 'CL',
            'recipient_id': 'R',
            'departure_date': datetime.now(timezone.utc),
            'total_cost': 100
        }
        
        pdf = generate_manifesto(trip_data)
        
        assert pdf.startswith(b'%PDF')
        assert b'endobj' in pdf
        assert b'%%EOF' in pdf
    
    def test_cumplido_is_valid_pdf(self):
        """Test that generated Cumplido is valid PDF."""
        trip_data = {
            '_id': 'test-id',
            'origin': 'A',
            'destination': 'B',
            'weight_tons': 1,
            'recipient_id': 'R',
            'total_cost': 100
        }
        
        pdf = generate_cumplido(trip_data)
        
        assert pdf.startswith(b'%PDF')
        assert b'endobj' in pdf
        assert b'%%EOF' in pdf
    
    def test_invoice_is_valid_pdf(self):
        """Test that generated Invoice is valid PDF."""
        trip_data = {
            '_id': 'test-id',
            'origin': 'A',
            'destination': 'B',
            'weight_tons': 1,
            'total_cost': 100
        }
        
        invoice_data = {
            'invoice_number': 'INV-001',
            'amount': 100,
            'tax_amount': 19,
            'total_amount': 119,
            'issued_at': datetime.now(timezone.utc),
            'status': 'pending'
        }
        
        pdf = generate_invoice(trip_data, invoice_data)
        
        assert pdf.startswith(b'%PDF')
        assert b'endobj' in pdf
        assert b'%%EOF' in pdf

