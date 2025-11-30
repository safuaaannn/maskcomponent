-- Simple SQL Query for pgAdmin (works with or without request_id column)
-- Copy and paste this into pgAdmin Query Tool

-- If request_id column exists:
SELECT 
    user_id,
    gender,
    request_id,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || upper_body_mask as upper_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || lower_body_mask as lower_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/' || request_id || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs;

-- If request_id column does NOT exist (fallback):
-- This constructs request_id from pattern: test-{user_id}-{gender}
SELECT 
    user_id,
    gender,
    'test-' || user_id || '-' || gender as request_id,
    'http://127.0.0.1:9000/masks/' || user_id || '/test-' || user_id || '-' || gender || '/' || upper_body_mask as upper_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/test-' || user_id || '-' || gender || '/' || lower_body_mask as lower_body_url,
    'http://127.0.0.1:9000/masks/' || user_id || '/test-' || user_id || '-' || gender || '/' || ethnic_combined_mask as ethnic_combined_url
FROM user_mask_outputs;

-- To change IP, replace '127.0.0.1' with your IP:
-- Example: 'http://192.168.1.100:9000/masks/'

