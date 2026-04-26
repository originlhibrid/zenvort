#!/bin/bash

echo "═══════════════════════════════════════════════════════════"
echo "1. DOCKER SERVICES"
echo "═══════════════════════════════════════════════════════════"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "--- Exited Containers ---"
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -v "Up"
echo ""
echo "--- Worker Logs (tail 50) ---"
docker logs zenvort-worker --tail 50 2>&1
echo ""
echo "--- API Logs (tail 50) ---"
docker logs zenvort-api --tail 50 2>&1

echo "═══════════════════════════════════════════════════════════"
echo "2. PORT AVAILABILITY"
echo "═══════════════════════════════════════════════════════════"
ss -tlnp | grep -E '3000|3001|5432|6379|5173'

echo "═══════════════════════════════════════════════════════════"
echo "3. BINARIES INSIDE WORKER CONTAINER"
echo "═══════════════════════════════════════════════════════════"
docker exec zenvort-worker bash -c "
  echo '--- soffice ---' && which soffice && soffice --version &&
  echo '--- pdftoppm ---' && which pdftoppm && pdftoppm -v 2>&1 &&
  echo '--- pdftotext ---' && which pdftotext && pdftotext -v 2>&1 &&
  echo '--- pandoc ---' && which pandoc && pandoc --version | head -1 &&
  echo '--- ffmpeg ---' && which ffmpeg && ffmpeg -version | head -1 &&
  echo '--- convert (ImageMagick) ---' && which convert && convert --version | head -1 &&
  echo '--- gs (Ghostscript) ---' && which gs && gs --version &&
  echo '--- sharp (Node) ---' && node -e \"require('sharp'); console.log('sharp OK')\" &&
  echo '--- node ---' && node --version &&
  echo '--- tsx ---' && npx tsx --version 2>&1 | head -1
"

echo "═══════════════════════════════════════════════════════════"
echo "4. IMAGEMAGICK PDF POLICY"
echo "═══════════════════════════════════════════════════════════"
docker exec zenvort-worker bash -c "
  grep -i 'PDF\|PS\|EPS' /etc/ImageMagick-6/policy.xml || echo 'policy.xml not found or no PDF entries'
"

echo "═══════════════════════════════════════════════════════════"
echo "5. DATABASE"
echo "═══════════════════════════════════════════════════════════"
docker exec zenvort-api sh -c "
  node -e \"
    const { PrismaClient } = require('@prisma/client');
    const db = new PrismaClient();
    db.\\\$connect().then(() => { console.log('DB OK'); process.exit(0); })
      .catch(e => { console.error('DB FAIL', e.message); process.exit(1); });
  \"
"
docker exec zenvort-api sh -c "npx prisma migrate status --schema=./packages/db/prisma/schema.prisma"
docker exec zenvort-api sh -c "
  echo \"
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'Job'
    ORDER BY ordinal_position;
  \" | npx prisma db execute --stdin --schema=./packages/db/prisma/schema.prisma
"

echo "═══════════════════════════════════════════════════════════"
echo "6. REDIS"
echo "═══════════════════════════════════════════════════════════"
docker exec zenvort-worker bash -c "
  node -e \"
    const Redis = require('ioredis');
    const r = new Redis(process.env.REDIS_URL || 'redis://redis:6379');
    r.ping().then(res => { console.log('Redis OK:', res); process.exit(0); })
      .catch(e => { console.error('Redis FAIL', e.message); process.exit(1); });
  \"
"
docker exec zenvort-worker bash -c "
  node -e \"
    const { Queue } = require('bullmq');
    const q = new Queue('conversions', { connection: { host: 'redis', port: 6379 } });
    q.getJobCounts().then(counts => { console.log('Queue counts:', counts); process.exit(0); });
  \"
"

echo "═══════════════════════════════════════════════════════════"
echo "7. R2 CONNECTIVITY"
echo "═══════════════════════════════════════════════════════════"
docker exec zenvort-worker bash -c "
  node -e \"
    const { S3Client, ListObjectsV2Command } = require('@aws-sdk/client-s3');
    const s3 = new S3Client({
      region: 'auto',
      endpoint: 'https://' + process.env.R2_ACCOUNT_ID + '.r2.cloudflarestorage.com',
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
      }
    });
    s3.send(new ListObjectsV2Command({ Bucket: process.env.R2_BUCKET_NAME, MaxKeys: 1 }))
      .then(() => { console.log('R2 OK'); process.exit(0); })
      .catch(e => { console.error('R2 FAIL', e.message); process.exit(1); });
  \"
"

echo "═══════════════════════════════════════════════════════════"
echo "8. API HEALTH"
echo "═══════════════════════════════════════════════════════════"
curl -s http://localhost:3000/health | jq .
echo ""
curl -s http://localhost:3001/metrics | jq .

echo "═══════════════════════════════════════════════════════════"
echo "9. DISK SPACE"
echo "═══════════════════════════════════════════════════════════"
df -h /
echo ""
docker exec zenvort-worker bash -c "
  ls -la /tmp/zenvort/ 2>/dev/null || echo '/tmp/zenvort/ does not exist'
  touch /tmp/zenvort/.writetest && echo 'writable OK' && rm /tmp/zenvort/.writetest
"
echo ""
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

