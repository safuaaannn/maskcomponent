-- SQL Query for pgAdmin: Get Full Mask URLs
-- Copy and paste this into pgAdmin Query Tool
-- ✅ Schema updated: request_id column now exists!

-- Option 1: Get all users with full URLs
SELECT 
    user_id,
    gender,
    request_id,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || upper_body_mask as upper_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || lower_body_mask as lower_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs;

-- Option 2: For specific user
SELECT 
    user_id,
    gender,
    request_id,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || upper_body_mask as upper_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || lower_body_mask as lower_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs
WHERE user_id = '1';

-- Option 3: To change IP, replace '127.0.0.1' with your IP
-- Example: 'http://192.168.1.100:9000/masks/'
SELECT 
    user_id,
    gender,
    request_id,
    'http://YOUR_IP:9000/masks/' || user_id || '/' || request_id || '/' || upper_body_mask as upper_body_url,
    'http://YOUR_IP:9000/masks/' || user_id || '/' || request_id || '/' || lower_body_mask as lower_body_url,
    'http://YOUR_IP:9000/masks/' || user_id || '/' || request_id || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs;

-- Option 4: Fallback if request_id is NULL (constructs from pattern)
SELECT 
    user_id,
    gender,
    COALESCE(request_id, 'test-' || user_id || '-' || gender) as request_id,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || COALESCE(request_id, 'test-' || user_id || '-' || gender) || '/' || upper_body_mask as upper_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || COALESCE(request_id, 'test-' || user_id || '-' || gender) || '/' || lower_body_mask as lower_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || COALESCE(request_id, 'test-' || user_id || '-' || gender) || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs;

