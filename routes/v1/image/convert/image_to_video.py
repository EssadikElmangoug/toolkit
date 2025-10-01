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



from flask import Blueprint, request, current_app
from app_utils import *
import logging
import os
import time
import uuid
from services.v1.image.convert.image_to_video import process_image_to_video
from services.authentication import authenticate
from services.cloud_storage import upload_file

v1_image_convert_video_bp = Blueprint('v1_image_convert_video', __name__)
logger = logging.getLogger(__name__)

def force_queue_task(f):
    """Custom decorator that forces jobs to be queued instead of executed immediately"""
    def wrapper(*args, **kwargs):
        job_id = str(uuid.uuid4())
        data = request.json if request.is_json else {}
        pid = os.getpid()
        start_time = time.time()
        
        # Always queue the job by ensuring webhook_url exists (even if empty)
        if 'webhook_url' not in data:
            data['webhook_url'] = ""
        
        # Get the queue from the app
        task_queue = current_app.task_queue
        queue_id = current_app.queue_id
        
        # Log job status as queued
        log_job_status(job_id, {
            "job_status": "queued",
            "job_id": job_id,
            "queue_id": queue_id,
            "process_id": pid,
            "response": None
        })
        
        # Create a wrapper function that properly handles the response
        def task_wrapper():
            try:
                # Log job status as running
                log_job_status(job_id, {
                    "job_status": "running",
                    "job_id": job_id,
                    "queue_id": queue_id,
                    "process_id": pid,
                    "response": None
                })
                
                # Execute the actual function
                response = f(job_id=job_id, data=data, *args, **kwargs)
                run_time = time.time() - start_time
                
                # Create response data
                response_data = {
                    "endpoint": response[1],
                    "code": response[2],
                    "id": data.get("id"),
                    "job_id": job_id,
                    "response": response[0] if response[2] == 200 else None,
                    "message": "success" if response[2] == 200 else response[0],
                    "pid": pid,
                    "queue_id": queue_id,
                    "run_time": round(run_time, 3),
                    "queue_time": 0,
                    "total_time": round(run_time, 3),
                    "queue_length": task_queue.qsize(),
                    "build_number": "1.0.0"
                }
                
                # Log job status as done
                log_job_status(job_id, {
                    "job_status": "done",
                    "job_id": job_id,
                    "queue_id": queue_id,
                    "process_id": pid,
                    "response": response_data
                })
                
                return response
                
            except Exception as e:
                # Log job status as error
                log_job_status(job_id, {
                    "job_status": "error",
                    "job_id": job_id,
                    "queue_id": queue_id,
                    "process_id": pid,
                    "response": {"error": str(e)}
                })
                raise
        
        # Add to queue
        task_queue.put((job_id, data, task_wrapper, start_time))
        
        return {
            "code": 202,
            "id": data.get("id"),
            "job_id": job_id,
            "message": "Job queued successfully",
            "pid": pid,
            "queue_id": queue_id,
            "queue_length": task_queue.qsize(),
            "build_number": "1.0.0"
        }, 202
    return wrapper

@v1_image_convert_video_bp.route('/v1/image/convert/video', methods=['POST'])
@v1_image_convert_video_bp.route('/v1/image/transform/video', methods=['POST']) #depleft for backwards compatibility, do not use.
@authenticate
@validate_payload({
    "type": "object",
    "properties": {
        "image_url": {"type": "string", "format": "uri"},
        "length": {"type": "number", "minimum": 0.1, "maximum": 400},
        "frame_rate": {"type": "integer", "minimum": 15, "maximum": 60},
        "zoom_speed": {"type": "number", "minimum": 0, "maximum": 100},
        "webhook_url": {"type": "string", "format": "uri"},
        "id": {"type": "string"}
    },
    "required": ["image_url"],
    "additionalProperties": False
})
@force_queue_task
def image_to_video(job_id, data):
    image_url = data.get('image_url')
    length = data.get('length', 5)
    frame_rate = data.get('frame_rate', 30)
    zoom_speed = data.get('zoom_speed', 3) / 100
    webhook_url = data.get('webhook_url')
    id = data.get('id')

    logger.info(f"Job {job_id}: Received image to video request for {image_url}")

    try:
        # Process image to video conversion
        output_filename = process_image_to_video(
            image_url, length, frame_rate, zoom_speed, job_id, webhook_url
        )

        # Upload the resulting file using the unified upload_file() method
        cloud_url = upload_file(output_filename)
        
        # Extract filename for download
        filename = os.path.basename(output_filename)

        # Log the successful upload
        logger.info(f"Job {job_id}: Converted video uploaded to cloud storage: {cloud_url}")
        logger.info(f"Job {job_id}: Filename for download: {filename}")

        # Return both cloud URL and filename for download
        response_data = {
            "download_url": cloud_url,
            "filename": filename,
            "message": "Video conversion completed successfully"
        }
        
        return response_data, "/v1/image/convert/video", 200
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error processing image to video: {str(e)}", exc_info=True)
        return str(e), "/v1/image/convert/video", 500
