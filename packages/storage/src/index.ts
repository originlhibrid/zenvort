import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  GetObjectCommandOutput,
} from "@aws-sdk/client-s3";
import { createWriteStream } from "fs";
import { pipeline } from "stream/promises";
import { Readable } from "stream";

const s3 = new S3Client({
  region: "auto",
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});

const bucket = process.env.R2_BUCKET_NAME!;
const publicUrl = process.env.R2_PUBLIC_URL!;

export async function uploadFile(
  key: string,
  filePath: string,
  mimeType: string
): Promise<string> {
  const { createReadStream } = await import("fs");
  const fileStream = createReadStream(filePath);

  await s3.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: fileStream,
      ContentType: mimeType,
    })
  );

  return `${publicUrl}/${key}`;
}

export async function downloadFile(key: string, destPath: string): Promise<void> {
  const response: GetObjectCommandOutput = await s3.send(
    new GetObjectCommand({ Bucket: bucket, Key: key })
  );

  const body = response.Body;

  if (!body) {
    throw new Error(`R2 response body is empty for key: ${key}`);
  }

  // Cast to Readable — S3 SDK always returns a streaming body with pipe()
  const bodyStream = body as unknown as Readable;
  const writeStream = createWriteStream(destPath);

  await pipeline(bodyStream, writeStream);
}

export async function deleteFile(key: string): Promise<void> {
  await s3.send(new DeleteObjectCommand({ Bucket: bucket, Key: key }));
}

export async function getSignedUrl(
  key: string,
  expiresInSeconds: number
): Promise<string> {
  const { getSignedUrl } = await import("@aws-sdk/s3-request-presigner");
  const command = new GetObjectCommand({ Bucket: bucket, Key: key });
  return getSignedUrl(s3, command, { expiresIn: expiresInSeconds });
}