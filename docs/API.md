# API Documentation

## Message Formats

### Input Message (mask_input topic)

**Required Fields:**
- `user_id` (string): Unique user identifier
- `image` (object): Image data with type and data fields

**Optional Fields:**
- `gender` (string): User gender (default: "other")
- `request_id` (string): Unique request identifier (auto-generated if not provided)
- `mask_types` (array): List of mask types to generate (default: ["upper_body", "upper_body_tshirts", "upper_body_coat", "lower_body", "ethnic_combined", "baggy_lower", "dress"])

**Image Object:**
- `type` (string): Either "url" or "base64"
- `data` (string): URL or base64-encoded image data

**Example:**
```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "mask_types": ["upper_body", "upper_body_tshirts", "upper_body_coat", "lower_body", "ethnic_combined", "baggy_lower", "dress"],
  "image": {
    "type": "url",
    "data": "http://example.com/image.jpg"
  }
}
```

### Output Message (mask_output topic)

**Success Response:**
```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "completed",
  "mask_paths": {
    "upper_body": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_mask.png",
    "upper_body_tshirts": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_tshirts_mask.png",
    "upper_body_coat": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_coat_mask.png",
    "lower_body": "http://127.0.0.1:9000/masks/123/req-123-001/lower_body_mask.png",
    "ethnic_combined": "http://127.0.0.1:9000/masks/123/req-123-001/ethnic_combined_mask.png",
    "baggy_lower": "http://127.0.0.1:9000/masks/123/req-123-001/baggy_lower_mask.png",
    "dress": "http://127.0.0.1:9000/masks/123/req-123-001/dress_mask.png"
  },
  "processed_at": "2025-11-26T12:00:00Z"
}
```

**Error Response:**
```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "failed",
  "error": "Error message here",
  "mask_paths": {},
  "processed_at": "2025-11-26T12:00:00Z"
}
```

## Supported Mask Types

- `upper_body`: Upper body segmentation mask (Shirts) - Masks upper clothes, arms, and neck region
- `upper_body_tshirts`: T-shirts mask - Masks upper clothes and arms with lower body coverage
- `upper_body_coat`: Coats/jackets mask - Masks upper clothes and arms with lower body coverage
- `lower_body`: Lower body segmentation mask (Pants) - Masks pants, legs, and skirt
- `ethnic_combined`: Combined ethnic segmentation mask - Masks upper and lower body with shoes included
- `baggy_lower`: Baggy pants mask - Masks lower body with larger dilation radius (includes shoes)
- `dress`: Full body dress mask - Masks dress, upper clothes, skirt, pants, arms, and neck region

## Error Codes

The service uses standard HTTP-like status codes in the `status` field:
- `completed`: Successfully processed
- `failed`: Processing failed (see `error` field for details)

## Rate Limiting

The service processes messages concurrently based on `SERVICE_CONCURRENCY` setting (default: 4). Messages are processed in order per partition.

