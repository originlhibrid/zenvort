#!/bin/bash

# 1. Health check
curl http://localhost:3000/health

echo ""

# 2. Submit a conversion job (replace test.pdf with any real file you have)
curl -X POST http://localhost:3000/jobs \
  -H "Authorization: Bearer test-key-123" \
  -F "file=@test.pdf" \
  -F "outputFormat=docx"

echo ""

# 3. Poll job status (replace JOB_ID with the id returned above)
curl http://localhost:3000/jobs/JOB_ID \
  -H "Authorization: Bearer test-key-123"
