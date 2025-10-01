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

from flask import Blueprint, request, send_file, jsonify, current_app
from app_utils import *
from services.authentication import authenticate
import logging
import os
import mimetypes
from urllib.parse import unquote

v1_storage_download_bp = Blueprint('v1_storage_download', __name__)
logger = logging.getLogger(__name__)

@v1_storage_download_bp.route('/v1/storage/download/<path:filename>', methods=['GET'])
@authenticate
def download_file(filename):
    """
    Download a file from local storage with API authentication.
    
    Args:
        filename (str): The filename to download (URL decoded)
    
    Returns:
        File download or error response
    """
    try:
        # URL decode the filename
        decoded_filename = unquote(filename)
        
        # Determine the storage location (same logic as save_file_locally)
        save_location = os.getenv('SAVE_LOCATION')
        if save_location:
            storage_dir = save_location
        else:
            # Check if we're in Docker with volume mount
            docker_storage = "/var/www/html/storage/app"
            if os.path.exists(docker_storage) and os.access(docker_storage, os.W_OK):
                storage_dir = docker_storage
            else:
                # Fallback to app directory storage
                storage_dir = "/app/storage"
        
        # Construct the full file path
        file_path = os.path.join(storage_dir, decoded_filename)
        
        logger.info(f"Download request for file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            return jsonify({"error": "Invalid file path"}), 400
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        logger.info(f"Serving file: {file_path} (size: {file_size} bytes, type: {mime_type})")
        
        # Return the file for download
        return send_file(
            file_path,
            as_attachment=True,
            download_name=decoded_filename,
            mimetype=mime_type
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

@v1_storage_download_bp.route('/v1/storage/list', methods=['GET'])
@authenticate
@queue_task_wrapper(bypass_queue=True)
def list_files(job_id, data=None):
    """
    List all files in the storage directory with API authentication.
    
    Args:
        job_id (str): Job ID assigned by queue_task_wrapper
        data (dict): Request data (not used for GET requests)
    
    Returns:
        List of files with metadata
    """
    try:
        # Determine the storage location (same logic as save_file_locally)
        save_location = os.getenv('SAVE_LOCATION')
        if save_location:
            storage_dir = save_location
        else:
            # Check if we're in Docker with volume mount
            docker_storage = "/var/www/html/storage/app"
            if os.path.exists(docker_storage) and os.access(docker_storage, os.W_OK):
                storage_dir = docker_storage
            else:
                # Fallback to app directory storage
                storage_dir = "/app/storage"
        
        logger.info(f"Job {job_id}: Listing files in: {storage_dir}")
        
        # Check if storage directory exists
        if not os.path.exists(storage_dir):
            return {"files": [], "storage_path": storage_dir}, "/v1/storage/list", 200
        
        # Get all files in the directory
        files = []
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                mime_type, _ = mimetypes.guess_type(file_path)
                
                files.append({
                    "filename": filename,
                    "size": file_stat.st_size,
                    "mime_type": mime_type or 'application/octet-stream',
                    "created": file_stat.st_ctime,
                    "modified": file_stat.st_mtime,
                    "download_url": f"/v1/storage/download/{filename}"
                })
        
        # Sort files by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        logger.info(f"Job {job_id}: Found {len(files)} files")
        
        return {
            "files": files,
            "storage_path": storage_dir,
            "total_files": len(files)
        }, "/v1/storage/list", 200
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error listing files: {str(e)}")
        return {"error": f"Failed to list files: {str(e)}"}, "/v1/storage/list", 500
