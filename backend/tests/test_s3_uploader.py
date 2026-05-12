"""
Tests for S3 uploader module.

Tests cover:
- PDF upload to S3
- Presigned URL generation
- Error handling
- Bucket configuration
"""

import os
import pytest
import boto3
from moto import mock_s3
from src.infrastructure.s3_uploader import S3Uploader, S3Error, get_s3_uploader


@mock_s3
def test_uploader_initialization():
    """Test S3Uploader initialization."""
    # Create mock S3 bucket
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    
    # Set environment variable
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        assert uploader.bucket_name == 'test-bucket'
        assert uploader.region == 'us-east-1'
        assert uploader.s3_client is not None
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_uploader_initialization_with_params():
    """Test S3Uploader initialization with explicit parameters."""
    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(
        Bucket='custom-bucket',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    
    uploader = S3Uploader(bucket_name='custom-bucket', region='us-west-2')
    assert uploader.bucket_name == 'custom-bucket'
    assert uploader.region == 'us-west-2'


@mock_s3
def test_upload_pdf_success():
    """Test successful PDF upload."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        pdf_content = b'%PDF-1.4\n%Mock PDF content'
        key = 'documents/test-order.pdf'
        
        result = uploader.upload_pdf(key, pdf_content)
        
        assert 's3://test-bucket/documents/test-order.pdf' in result
        
        # Verify object was created in S3
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.get_object(Bucket='test-bucket', Key=key)
        assert response['Body'].read() == pdf_content
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_upload_pdf_with_metadata():
    """Test PDF upload with metadata."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        pdf_content = b'%PDF-1.4\n%Test PDF'
        key = 'documents/test-with-metadata.pdf'
        metadata = {'trip-id': '12345', 'document-type': 'order'}
        
        result = uploader.upload_pdf(key, pdf_content, metadata=metadata)
        
        assert 's3://test-bucket/' in result
        
        # Verify metadata
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.head_object(Bucket='test-bucket', Key=key)
        assert response['Metadata']['trip-id'] == '12345'
        assert response['Metadata']['document-type'] == 'order'
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_upload_pdf_private_acl():
    """Test that uploaded PDFs are private."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        pdf_content = b'%PDF-1.4\n%Private PDF'
        key = 'documents/private-test.pdf'
        
        uploader.upload_pdf(key, pdf_content)
        
        # Verify ACL is private
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.get_object_acl(Bucket='test-bucket', Key=key)
        
        # Should only have owner as grantee
        assert len(response['Grants']) >= 1
        assert all(g['Grantee'].get('Type') != 'Group' for g in response['Grants'])
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_upload_pdf_encryption():
    """Test that uploaded PDFs are encrypted."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        pdf_content = b'%PDF-1.4\n%Encrypted PDF'
        key = 'documents/encrypted-test.pdf'
        
        uploader.upload_pdf(key, pdf_content)
        
        # Verify encryption
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.head_object(Bucket='test-bucket', Key=key)
        assert response.get('ServerSideEncryption') == 'AES256'
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_generate_presigned_url():
    """Test presigned URL generation."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Upload a PDF first
        pdf_content = b'%PDF-1.4\n%Test PDF'
        key = 'documents/test-presigned.pdf'
        uploader.upload_pdf(key, pdf_content)
        
        # Generate presigned URL
        url = uploader.generate_presigned_url(key, expiration=3600)
        
        assert 'test-bucket' in url
        assert key in url
        # Check for signature parameters (moto uses different format than real AWS)
        assert 'Signature' in url or 'X-Amz-Signature' in url
        assert 'Expires' in url or 'X-Amz-Expires' in url
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_generate_presigned_url_expiration():
    """Test presigned URL with custom expiration."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Upload a PDF
        key = 'documents/test-expiry.pdf'
        uploader.upload_pdf(key, b'%PDF test')
        
        # Generate URLs with different expirations
        url_short = uploader.generate_presigned_url(key, expiration=60)
        url_long = uploader.generate_presigned_url(key, expiration=3600)
        
        # Both should be valid presigned URLs
        assert 'Expires' in url_short or 'X-Amz-Expires' in url_short
        assert 'Expires' in url_long or 'X-Amz-Expires' in url_long
        # URLs should contain the key
        assert key in url_short
        assert key in url_long
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_download_pdf():
    """Test PDF download from S3."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Upload a PDF
        pdf_content = b'%PDF-1.4\n%Download test'
        key = 'documents/test-download.pdf'
        uploader.upload_pdf(key, pdf_content)
        
        # Download the PDF
        downloaded_content = uploader.download_pdf(key)
        
        assert downloaded_content == pdf_content
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_download_pdf_not_found():
    """Test download of non-existent PDF."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        with pytest.raises(S3Error) as exc_info:
            uploader.download_pdf('non-existent-key.pdf')
        
        assert 'not found' in str(exc_info.value)
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_delete_pdf():
    """Test PDF deletion from S3."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Upload a PDF
        key = 'documents/test-delete.pdf'
        uploader.upload_pdf(key, b'%PDF test')
        
        # Delete the PDF
        result = uploader.delete_pdf(key)
        assert result is True
        
        # Verify it's deleted
        s3 = boto3.client('s3', region_name='us-east-1')
        with pytest.raises(Exception):
            s3.head_object(Bucket='test-bucket', Key=key)
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_multiple_uploads():
    """Test multiple PDF uploads."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Upload multiple PDFs
        keys = []
        for i in range(5):
            key = f'documents/test-multi-{i}.pdf'
            uploader.upload_pdf(key, f'PDF content {i}'.encode())
            keys.append(key)
        
        # Verify all uploads
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.list_objects_v2(Bucket='test-bucket', Prefix='documents/')
        
        assert len(response.get('Contents', [])) >= 5
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_upload_large_pdf():
    """Test upload of large PDF (1MB)."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        uploader = S3Uploader()
        
        # Create 1MB PDF content
        large_pdf = b'%PDF\n' + (b'x' * (1024 * 1024))
        key = 'documents/large-pdf.pdf'
        
        result = uploader.upload_pdf(key, large_pdf)
        
        assert 's3://test-bucket/' in result
        
        # Verify upload
        s3 = boto3.client('s3', region_name='us-east-1')
        response = s3.head_object(Bucket='test-bucket', Key=key)
        assert response['ContentLength'] == len(large_pdf)
    finally:
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


@mock_s3
def test_singleton_pattern():
    """Test that get_s3_uploader returns singleton."""
    # Setup
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='test-bucket')
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    try:
        # Get two instances
        uploader1 = get_s3_uploader()
        uploader2 = get_s3_uploader()
        
        # Should be the same instance
        assert uploader1 is uploader2
    finally:
        # Cleanup
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
        if 'AWS_REGION' in os.environ:
            del os.environ['AWS_REGION']


def test_uploader_missing_bucket_env():
    """Test error when bucket name not provided."""
    # Ensure env var is not set
    if 'S3_BUCKET_NAME' in os.environ:
        del os.environ['S3_BUCKET_NAME']
    
    with pytest.raises(S3Error) as exc_info:
        S3Uploader()
    
    assert 'S3_BUCKET_NAME' in str(exc_info.value)


@mock_s3
def test_uploader_nonexistent_bucket():
    """Test error when bucket doesn't exist."""
    os.environ['S3_BUCKET_NAME'] = 'nonexistent-bucket'
    
    try:
        with pytest.raises(S3Error):
            uploader = S3Uploader()
            uploader.upload_pdf('test.pdf', b'content')
    finally:
        # Cleanup
        del os.environ['S3_BUCKET_NAME']
