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
import json
import logging
from flask import Blueprint, request
from config import LOCAL_STORAGE_PATH
from services.authentication import authenticate
from app_utils import queue_task_wrapper, validate_payload

v1_toolkit_job_status_bp = Blueprint('v1_toolkit_job_status', __name__)
logger = logging.getLogger(__name__)

@v1_toolkit_job_status_bp.route('/v1/toolkit/job/status', methods=['POST'])
@authenticate
@validate_payload({
    "type": "object",
    "properties": {
        "job_id": {
            "type": "string"
        }
    },
    "required": ["job_id"],
})
@queue_task_wrapper(bypass_queue=True)
def get_job_status(job_id, data):

    get_job_id = data.get('job_id')

    logger.info(f"Retrieving status for job {get_job_id}")
    
    try:
        # Construct the path to the job status file
        job_file_path = os.path.join(LOCAL_STORAGE_PATH, 'jobs', f"{get_job_id}.json")
        
        # Check if the job file exists
        if not os.path.exists(job_file_path):
            return {"error": "Job not found", "job_id": get_job_id}, "/v1/toolkit/job/status", 404
        
        # Read the job status file
        with open(job_file_path, 'r') as file:
            job_status = json.load(file)
        
        # Enhance the response with download information if job is completed
        if job_status.get("job_status") == "done" and job_status.get("response"):
            response_data = job_status.get("response", {})
            
            # First check if filename is already at the top level
            if "filename" in response_data:
                filename = response_data["filename"]
                base_url = os.getenv('API_BASE_URL', 'http://localhost:8080')
                download_url = f"{base_url}/v1/storage/download/{filename}"
                
                # Add to top level for easier access
                job_status["filename"] = filename
                job_status["download_url"] = download_url
                
                logger.info(f"Job {get_job_id}: Found filename at top level: {filename}")
            else:
                # Navigate through nested response structure to find the actual response
                actual_response = response_data
                while isinstance(actual_response, dict) and "response" in actual_response:
                    if isinstance(actual_response["response"], dict):
                        actual_response = actual_response["response"]
                    else:
                        break
                
                # Check if we found the actual response with filename
                if isinstance(actual_response, dict) and "filename" in actual_response:
                    # Add download URL to the response
                    filename = actual_response["filename"]
                    base_url = os.getenv('API_BASE_URL', 'http://localhost:8080')
                    download_url = f"{base_url}/v1/storage/download/{filename}"
                    actual_response["download_url"] = download_url
                    
                    # Also add filename and download_url to the top level for easier access
                    job_status["filename"] = filename
                    job_status["download_url"] = download_url
                    
                    # Update the job status with the enhanced response
                    job_status["response"] = response_data
                    
                    logger.info(f"Job {get_job_id}: Enhanced response with filename from nested structure: {filename}")
                else:
                    logger.warning(f"Job {get_job_id}: No filename found in response structure")
        
        # Return the job status file content directly
        return job_status, "/v1/toolkit/job/status", 200
        
    except Exception as e:
        logger.error(f"Error retrieving status for job {get_job_id}: {str(e)}")
        return {"error": f"Failed to retrieve job status: {str(e)}"}, "/v1/toolkit/job/status", 500 