const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const fs = require('fs');
const s3 = new S3Client({
  region: 'auto',
  endpoint: 'https://' + process.env.R2_ACCOUNT_ID + '.r2.cloudflarestorage.com',
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY
  }
});
const bucket = process.env.R2_BUCKET_NAME;
const key = 'inputs/d680068f-b90d-423a-9e34-3f52f2eb73f9/test.pdf';
const dest = '/tmp/test_dl.pdf';
console.log('bucket:', bucket, 'key:', key);
s3.send(new GetObjectCommand({ Bucket: bucket, Key: key }))
  .then(r => {
    console.log('Got response');
    const ws = fs.createWriteStream(dest);
    r.Body.pipe(ws);
    ws.on('finish', () => {
      const stats = fs.statSync(dest);
      console.log('SUCCESS - downloaded', stats.size, 'bytes to', dest);
    });
    ws.on('error', e => console.error('WRITE ERROR:', e.message));
  })
  .catch(e => {
    console.error('S3 ERROR:', e.message, e.$metadata ? JSON.stringify(e.$metadata) : '');
  });