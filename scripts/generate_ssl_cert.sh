#!/bin/bash
# Generate self-signed SSL certificate for HAProxy (development/testing)
# For production, replace with certificates from a trusted CA (e.g., Let's Encrypt)

openssl req -x509 -newkey rsa:4096 \
  -keyout config/ssl/key.pem \
  -out config/ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=localhost/O=TrustWise/C=US"

# Combine into HAProxy PEM format
cat config/ssl/cert.pem config/ssl/key.pem > config/ssl/server.pem

echo "✅ SSL certificate generated at config/ssl/server.pem"
