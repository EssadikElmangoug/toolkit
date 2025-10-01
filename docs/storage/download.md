# Storage Download Endpoints

## Overview

The storage download endpoints provide secure, API-authenticated access to files saved locally by the application. These endpoints replace cloud storage URLs with local file access while maintaining security through API key authentication.

## Endpoints

### 1. Download File

**URL:** `/v1/storage/download/<filename>`  
**Method:** `GET`  
**Authentication:** Required (X-API-Key header)

Downloads a specific file from local storage.

#### Request

**Headers:**
- `X-API-Key` (required): Your API key for authentication

**Path Parameters:**
- `filename` (required): The filename to download (URL encoded)

#### Response

**Success (200):**
- Returns the file as a download attachment
- Content-Type: Determined by file MIME type
- Content-Disposition: attachment; filename="original_filename"

**Error Responses:**
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: File does not exist
- `400 Bad Request`: Invalid file path
- `500 Internal Server Error`: Server error during download

#### Example Request

```bash
curl -X GET \
  -H "X-API-Key: YOUR_API_KEY" \
  "https://your-domain.com/v1/storage/download/image_20250101_143022.jpg"
```

#### Example Response

```
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Disposition: attachment; filename="image_20250101_143022.jpg"
Content-Length: 1234567

[Binary file content]
```

### 2. List Files

**URL:** `/v1/storage/list`  
**Method:** `GET`  
**Authentication:** Required (X-API-Key header)

Lists all files available in the storage directory.

#### Request

**Headers:**
- `X-API-Key` (required): Your API key for authentication

#### Response

**Success (200):**
```json
{
  "code": 200,
  "endpoint": "/v1/storage/list",
  "id": null,
  "job_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "message": "success",
  "pid": 12345,
  "queue_id": 1234567890,
  "queue_length": 0,
  "response": {
    "files": [
      {
        "filename": "image_20250101_143022.jpg",
        "size": 1234567,
        "mime_type": "image/jpeg",
        "created": 1704112222.123,
        "modified": 1704112222.123,
        "download_url": "/v1/storage/download/image_20250101_143022.jpg"
      },
      {
        "filename": "video_20250101_144500.mp4",
        "size": 9876543,
        "mime_type": "video/mp4",
        "created": 1704112700.456,
        "modified": 1704112700.456,
        "download_url": "/v1/storage/download/video_20250101_144500.mp4"
      }
    ],
    "storage_path": "/var/www/html/storage/app",
    "total_files": 2
  },
  "run_time": 0.001,
  "total_time": 0.001,
  "queue_time": 0,
  "build_number": "1.0.0"
}
```

#### Example Request

```bash
curl -X GET \
  -H "X-API-Key: YOUR_API_KEY" \
  "https://your-domain.com/v1/storage/list"
```

## File Storage Locations

The system automatically determines the storage location based on environment:

1. **SAVE_LOCATION environment variable** (highest priority)
2. **Docker volume mount** (`/var/www/html/storage/app`)
3. **App directory fallback** (`/app/storage`)

## File Naming Convention

Files are saved with timestamps to prevent conflicts:
- Format: `{original_name}_{YYYYMMDD_HHMMSS}.{extension}`
- Example: `image_20250101_143022.jpg`

## Security Features

- **API Key Authentication**: All endpoints require valid API key
- **Path Validation**: Prevents directory traversal attacks
- **File Existence Checks**: Validates files exist before serving
- **MIME Type Detection**: Proper content-type headers

## Configuration

### Environment Variables

- `SAVE_LOCATION`: Custom storage directory path
- `API_BASE_URL`: Base URL for generating download URLs (default: `http://localhost:8080`)

### Docker Compose Example

```yaml
services:
  ncat:
    environment:
      - SAVE_LOCATION=/vps-home
      - API_BASE_URL=https://your-domain.com
    volumes:
      - /home:/vps-home
```

## Integration with Upload Functions

When files are uploaded using the `upload_file()` function, they now return download URLs instead of file paths:

```python
# Before (cloud storage)
cloud_url = upload_file("temp_file.mp4")
# Returns: "https://bucket.s3.amazonaws.com/file.mp4"

# After (local storage)
download_url = upload_file("temp_file.mp4")
# Returns: "https://your-domain.com/v1/storage/download/video_20250101_143022.mp4"
```

## Error Handling

All endpoints include comprehensive error handling:
- Invalid API keys return 401
- Missing files return 404
- Server errors return 500 with error details
- All errors are logged for debugging

## Usage Notes

- Files are served with `Content-Disposition: attachment` to force download
- Large files are streamed efficiently
- The list endpoint sorts files by modification time (newest first)
- All file operations are logged for audit purposes
