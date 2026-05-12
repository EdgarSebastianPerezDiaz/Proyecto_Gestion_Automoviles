"""
S3 uploader module - handles PDF uploads to AWS S3 with presigned URLs.

This module provides functionality to:
- Upload PDF documents to S3 with proper access controls
- Generate presigned URLs for secure document access
- Handle S3 client initialization and error handling
"""

import os
import boto3
from typing import Optional
from datetime import timedelta
from botocore.exceptions import ClientError, NoCredentialsError


class S3Error(Exception):
    """Base exception for S3 operations."""
    pass


class S3Uploader:
    """Handler for uploading PDFs to AWS S3 and generating presigned URLs."""
    
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize S3 uploader.
        
        Args:
            bucket_name: S3 bucket name (defaults to S3_BUCKET_NAME env var)
            region: AWS region (defaults to AWS_REGION env var or us-east-1)
            
        Raises:
            S3Error: If bucket name is not provided and env var not set
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        if not self.bucket_name:
            raise S3Error("S3_BUCKET_NAME must be provided or set as environment variable")
        
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
        except NoCredentialsError:
            raise S3Error("AWS credentials not found. Configure AWS credentials or IAM role.")
        except Exception as e:
            raise S3Error(f"Failed to initialize S3 client: {str(e)}")
    
    def upload_pdf(
        self,
        key: str,
        content: bytes,
        content_type: str = 'application/pdf',
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload PDF document to S3.
        
        The object is stored with private ACL (not public). Access is controlled
        through IAM policies and presigned URLs.
        
        Args:
            key: S3 object key (e.g., 'documents/order-123.pdf')
            content: PDF content as bytes
            content_type: MIME type (default: 'application/pdf')
            metadata: Optional metadata dict (x-amz-meta-* headers)
            
        Returns:
            S3 URI (s3://bucket/key)
            
        Raises:
            S3Error: If upload fails
        """
        try:
            # Prepare extra arguments
            extra_args = {
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256',
                'ACL': 'private'  # Ensure objects are not publicly accessible
            }
            
            # Add metadata if provided
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                **extra_args
            )
            
            # Return S3 URI
            s3_uri = f"s3://{self.bucket_name}/{key}"
            return s3_uri
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchBucket':
                raise S3Error(f"S3 bucket does not exist: {self.bucket_name}")
            elif error_code == 'AccessDenied':
                raise S3Error(f"Access denied to S3 bucket: {self.bucket_name}")
            else:
                raise S3Error(f"Failed to upload PDF to S3: {str(e)}")
        except Exception as e:
            raise S3Error(f"Unexpected error uploading to S3: {str(e)}")
    
    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for secure document access.
        
        Presigned URLs allow temporary access to private S3 objects without
        exposing AWS credentials. They are URL-accessible and can be embedded
        in emails, shared via API, etc.
        
        Args:
            key: S3 object key (e.g., 'documents/order-123.pdf')
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL (valid for specified expiration time)
            
        Raises:
            S3Error: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise S3Error(f"Failed to generate presigned URL: {str(e)}")
        except Exception as e:
            raise S3Error(f"Unexpected error generating presigned URL: {str(e)}")
    
    def download_pdf(self, key: str) -> bytes:
        """
        Download PDF from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            PDF content as bytes
            
        Raises:
            S3Error: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchKey':
                raise S3Error(f"PDF not found in S3: {key}")
            else:
                raise S3Error(f"Failed to download PDF from S3: {str(e)}")
        except Exception as e:
            raise S3Error(f"Unexpected error downloading from S3: {str(e)}")
    
    def delete_pdf(self, key: str) -> bool:
        """
        Delete PDF from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful
            
        Raises:
            S3Error: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except Exception as e:
            raise S3Error(f"Failed to delete PDF from S3: {str(e)}")


# Singleton instance (lazy loaded)
_s3_uploader = None


def get_s3_uploader() -> S3Uploader:
    """
    Get or create S3 uploader singleton instance.
    
    Returns:
        S3Uploader instance
        
    Raises:
        S3Error: If initialization fails
    """
    global _s3_uploader
    if _s3_uploader is None:
        _s3_uploader = S3Uploader()
    return _s3_uploader
