#!/bin/sh

# Generate runtime config from environment variables
cat <<EOF > /usr/share/nginx/html/config.js
window.__RUNTIME_CONFIG__ = {
  API_BASE_URL: "${VITE_API_URL:-}"
};
EOF

echo "Generated runtime config:"
cat /usr/share/nginx/html/config.js

# Start nginx
exec nginx -g "daemon off;"
