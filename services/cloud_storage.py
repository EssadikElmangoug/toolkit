# Copyright (c) 2025 Stephen G. Pope
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.



import os
import logging
import shutil
from datetime import datetime
from abc import ABC, abstractmethod
from services.gcp_toolkit import upload_to_gcs
from services.s3_toolkit import upload_to_s3
from config import validate_env_vars
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def parse_s3_url(s3_url):
    """Parse S3 URL to extract bucket name, region, and endpoint URL."""
    parsed_url = urlparse(s3_url)
    
    # Extract bucket name from the host
    bucket_name = parsed_url.hostname.split('.')[0]
    
    # Extract region from the host
    region = parsed_url.hostname.split('.')[1]
    
    return bucket_name, region

class CloudStorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_path: str) -> str:
        pass

class GCPStorageProvider(CloudStorageProvider):
    def __init__(self):
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')

    def upload_file(self, file_path: str) -> str:
        return upload_to_gcs(file_path, self.bucket_name)

class S3CompatibleProvider(CloudStorageProvider):
    def __init__(self):

        self.endpoint_url = os.getenv('S3_ENDPOINT_URL')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.bucket_name = os.environ.get('S3_BUCKET_NAME', '')
        self.region = os.environ.get('S3_REGION', '')
        
        # Check if endpoint is Digital Ocean and bucket name or region is missing
        if (self.endpoint_url and 
            'digitalocean' in self.endpoint_url.lower() and 
            (not self.bucket_name or not self.region)):
            
            logger.info("Digital Ocean endpoint detected with missing bucket or region. Extracting from URL.")
            try:
                # Extract bucket name and region from URL like https://sgp-labs.nyc3.digitaloceanspaces.com
                parsed_url = urlparse(self.endpoint_url)
                hostname_parts = parsed_url.hostname.split('.')
                
                # The first part is the bucket name (sgp-labs)
                if not self.bucket_name:
                    self.bucket_name = hostname_parts[0]
                    logger.info(f"Extracted bucket name from URL: {self.bucket_name}")
                
                # The second part is the region (nyc3)
                if not self.region:
                    self.region = hostname_parts[1]
                    logger.info(f"Extracted region from URL: {self.region}")
                
            except Exception as e:
                logger.warning(f"Failed to parse Digital Ocean URL: {e}. Using provided values.")

    def upload_file(self, file_path: str) -> str:
        return upload_to_s3(file_path, self.endpoint_url, self.access_key, self.secret_key, self.bucket_name, self.region)

def get_storage_provider() -> CloudStorageProvider:
    
    if os.getenv('S3_ENDPOINT_URL'):

        if ('digitalocean' in os.getenv('S3_ENDPOINT_URL').lower()):

            validate_env_vars('S3_DO')
        else:
            validate_env_vars('S3')

        return S3CompatibleProvider()
    
    if os.getenv('GCP_BUCKET_NAME'):

        validate_env_vars('GCP')
        return GCPStorageProvider()
    
    raise ValueError(f"No cloud storage settings provided.")

def save_file_locally(file_path: str, local_storage_dir: str = None) -> str:
    """
    Save a file locally instead of uploading to cloud storage.
    
    Args:
        file_path: Path to the source file to save
        local_storage_dir: Directory to save files locally (default: from SAVE_LOCATION env var or auto-detect)
    
    Returns:
        str: Path to the saved file
    """
    try:
        # Determine the best storage location based on environment
        if local_storage_dir is None:
            # First check for SAVE_LOCATION environment variable
            save_location = os.getenv('SAVE_LOCATION')
            if save_location:
                local_storage_dir = save_location
                logger.info(f"Using SAVE_LOCATION environment variable: {local_storage_dir}")
                logger.info(f"Current user: {os.getuid()}:{os.getgid()}")
                logger.info(f"Directory exists: {os.path.exists(local_storage_dir)}")
                if os.path.exists(local_storage_dir):
                    logger.info(f"Directory writable: {os.access(local_storage_dir, os.W_OK)}")
            else:
                # Check if we're in Docker with volume mount
                docker_storage = "/var/www/html/storage/app"
                if os.path.exists(docker_storage) and os.access(docker_storage, os.W_OK):
                    local_storage_dir = docker_storage
                    logger.info("Using Docker volume mount for storage")
                else:
                    # Fallback to app directory storage
                    local_storage_dir = "/app/storage"
                    logger.info("Using app directory for storage")
        
        # Create local storage directory if it doesn't exist
        try:
            os.makedirs(local_storage_dir, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied creating directory {local_storage_dir}: {e}")
            logger.error("Please ensure the container has write permissions to the mounted directory")
            raise PermissionError(f"Cannot create storage directory {local_storage_dir}. Please check permissions.")
        
        # Generate a unique filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Create the destination path
        destination_path = os.path.join(local_storage_dir, unique_filename)
        
        logger.info(f"Saving file locally: {file_path} -> {destination_path}")
        
        # Copy the file to the local storage directory
        shutil.copy2(file_path, destination_path)
        
        logger.info(f"File saved successfully locally: {destination_path}")
        return destination_path
        
    except Exception as e:
        logger.error(f"Error saving file locally: {e}")
        raise

def upload_file(file_path: str) -> str:
    """
    Legacy function name - now saves files locally instead of uploading to cloud.
    This maintains backward compatibility while changing the behavior.
    Returns a download URL for the saved file.
    """
    saved_path = save_file_locally(file_path)
    
    # Extract just the filename from the saved path
    filename = os.path.basename(saved_path)
    
    # Return a download URL
    # Note: This assumes the API is running on the same host
    # In production, you might want to use a proper domain
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8080')
    download_url = f"{base_url}/v1/storage/download/{filename}"
    
    logger.info(f"Generated download URL: {download_url}")
    return download_url
    