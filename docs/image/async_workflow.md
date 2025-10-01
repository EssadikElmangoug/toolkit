# Asynchronous Image-to-Video Workflow

## Overview

The image-to-video conversion now supports asynchronous processing to handle long-running tasks without timeout errors. This workflow allows you to submit a job, get a job ID, and then check the status until completion.

## Workflow Steps

### 1. Submit Image-to-Video Job

**Endpoint:** `/v1/image/convert/video`  
**Method:** `POST`

Submit your image-to-video conversion request. The system will return a job ID immediately.

#### Request

```json
{
  "image_url": "https://example.com/image.jpg",
  "length": 60,
  "frame_rate": 30,
  "zoom_speed": 3
}
```

#### Response

```json
{
  "code": 202,
  "id": null,
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "response": null,
  "message": "Job queued successfully",
  "run_time": 0.001,
  "queue_time": 0,
  "total_time": 0.001,
  "pid": 12345,
  "queue_id": 1234567890,
  "queue_length": 1,
  "build_number": "1.0.0"
}
```

### 2. Check Job Status

**Endpoint:** `/v1/toolkit/job/status`  
**Method:** `POST`

Use the job ID to check the status of your conversion.

#### Request

```json
{
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6"
}
```

#### Response (Job Running)

```json
{
  "code": 200,
  "id": null,
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "response": {
    "job_status": "running",
    "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
    "queue_id": 1234567890,
    "process_id": 12345,
    "response": null
  },
  "message": "success",
  "run_time": 0.001,
  "queue_time": 0,
  "total_time": 0.001,
  "pid": 12345,
  "queue_id": 1234567890,
  "queue_length": 0,
  "build_number": "1.0.0"
}
```

#### Response (Job Completed)

```json
{
  "code": 200,
  "id": null,
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "response": {
    "job_status": "done",
    "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
    "queue_id": 1234567890,
    "process_id": 12345,
    "response": {
      "download_url": "https://toolkit.giganalyzer.com/v1/storage/download/video_20250101_143022.mp4",
      "filename": "video_20250101_143022.mp4",
      "message": "Video conversion completed successfully"
    }
  },
  "message": "success",
  "run_time": 45.123,
  "queue_time": 2.456,
  "total_time": 47.579,
  "pid": 12345,
  "queue_id": 1234567890,
  "queue_length": 0,
  "build_number": "1.0.0"
}
```

### 3. Download the File

Once the job is completed, you can download the file using either:

#### Option A: Use the Download URL from Status Response

```bash
curl -X GET -H "X-API-Key: YOUR_API_KEY" \
  "https://toolkit.giganalyzer.com/v1/storage/download/video_20250101_143022.mp4" \
  --output video.mp4
```

#### Option B: Use the Filename with Download Endpoint

```bash
curl -X GET -H "X-API-Key: YOUR_API_KEY" \
  "https://toolkit.giganalyzer.com/v1/storage/download/video_20250101_143022.mp4" \
  --output video.mp4
```

## Complete Example Workflow

### Step 1: Submit Job

```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "length": 60,
    "frame_rate": 30,
    "zoom_speed": 3
  }' \
  "https://toolkit.giganalyzer.com/v1/image/convert/video"
```

**Response:**
```json
{
  "code": 202,
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "message": "Job queued successfully"
}
```

### Step 2: Check Status (Polling)

```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6"
  }' \
  "https://toolkit.giganalyzer.com/v1/toolkit/job/status"
```

**Keep polling until `job_status` is "done"**

### Step 3: Download File

```bash
curl -X GET -H "X-API-Key: YOUR_API_KEY" \
  "https://toolkit.giganalyzer.com/v1/storage/download/video_20250101_143022.mp4" \
  --output video.mp4
```

## Job Status Values

- **`running`**: Job is currently being processed
- **`done`**: Job completed successfully
- **`error`**: Job failed (check error message)

## Error Handling

### Job Not Found (404)

```json
{
  "error": "Job not found",
  "job_id": "invalid-job-id"
}
```

### Job Failed

```json
{
  "job_status": "error",
  "error": "Error message describing what went wrong"
}
```

## Benefits

- ✅ **No Timeouts**: Long-running conversions won't timeout
- ✅ **Real-time Status**: Check progress anytime
- ✅ **Persistent Storage**: Files saved to VPS filesystem
- ✅ **Scalable**: Multiple jobs can be queued
- ✅ **Reliable**: Jobs persist across container restarts

## Polling Recommendations

- **Short jobs (< 30 seconds)**: Poll every 2-3 seconds
- **Medium jobs (30 seconds - 2 minutes)**: Poll every 5-10 seconds  
- **Long jobs (> 2 minutes)**: Poll every 15-30 seconds

## Webhook Support

You can also use webhooks to get notified when jobs complete:

```json
{
  "image_url": "https://example.com/image.jpg",
  "length": 60,
  "webhook_url": "https://your-server.com/webhook"
}
```

The webhook will receive the same response format as the status endpoint when the job completes.
