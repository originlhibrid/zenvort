import "dotenv/config";
import { Worker, Job as BullJob } from "bullmq";
import ffmpeg from "fluent-ffmpeg";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { db } from "@zenvort/db";
import { redisConnection, ConversionJobData } from "@zenvort/queue";
import { downloadFile, uploadFile } from "@zenvort/storage";
import { startCleanupCron } from "./cron/cleanup.js";

const execAsync = promisify(exec);

const VIDEO_AUDIO_FORMATS = ["mp4", "mov", "avi", "mkv", "webm", "mp3", "wav", "aac", "flac"];
const libreOfficeFormats = ['pdf', 'docx', 'doc', 'pptx', 'xlsx', 'odt', 'html', 'txt'];

async function sendWebhook(
  userId: string,
  jobId: string,
  status: 'DONE' | 'FAILED',
  outputUrl: string | undefined,
  error: string | undefined
): Promise<void> {
  try {
    const user = await db.user.findUnique({ where: { id: userId } });
    if (!user?.webhookUrl) return;

    const response = await fetch(user.webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobId,
        status,
        outputUrl,
        error,
        timestamp: new Date().toISOString(),
      }),
    });

    if (response.ok) {
      console.log(`Webhook delivered for job ${jobId} to ${user.webhookUrl}`);
    } else {
      console.error(`Webhook failed for job ${jobId}: ${response.status}`);
    }
  } catch (err) {
    console.error(`Webhook error for job ${jobId}:`, err);
  }
}

async function convertWithFFmpeg(inputPath: string, outputPath: string, outputFormat: string): Promise<void> {
  return new Promise((resolve, reject) => {
    ffmpeg(inputPath)
      .toFormat(outputFormat)
      .save(outputPath)
      .on("end", () => resolve())
      .on("error", (err) => reject(err));
  });
}

async function convertWithLibreOffice(inputPath: string, outputFormat: string): Promise<string> {
  const cmd = `libreoffice --headless --convert-to ${outputFormat} --outdir /tmp "${inputPath}"`;
  await execAsync(cmd);
  
  // LibreOffice renames the output file, find it
  const baseName = path.basename(inputPath, path.extname(inputPath));
  return `/tmp/${baseName}.${outputFormat}`;
}

async function processJob(job: BullJob<ConversionJobData>): Promise<void> {
  const { jobId, inputUrl, inputFormat, outputFormat } = job.data;
  let inputPath = "";
  let outputPath = "";
  let convertedPath = "";

  try {
    // 1. Update job status to PROCESSING
    await db.job.update({
      where: { id: jobId },
      data: { status: "PROCESSING" },
    });

    // 2. Download input file from R2
    const inputKey = inputUrl.replace(`${process.env.R2_PUBLIC_URL}/`, "");
    inputPath = `/tmp/${jobId}-input.${inputFormat}`;
    await downloadFile(inputKey, inputPath);

    outputPath = `/tmp/${jobId}-output.${outputFormat}`;

    // 3. Determine converter based on inputFormat
    if (VIDEO_AUDIO_FORMATS.includes(inputFormat) || VIDEO_AUDIO_FORMATS.includes(outputFormat)) {
      // 4. FFmpeg conversion
      await convertWithFFmpeg(inputPath, outputPath, outputFormat);
    } else if (libreOfficeFormats.includes(inputFormat)) {
      // 5. LibreOffice conversion
      convertedPath = await convertWithLibreOffice(inputPath, outputFormat);
      // If LibreOffice output path differs from expected, move it
      if (convertedPath !== outputPath) {
        const { createReadStream, createWriteStream } = await import("fs");
        const { pipeline } = await import("stream/promises");
        await pipeline(createReadStream(convertedPath), createWriteStream(outputPath));
      }
    } else {
      throw new Error(`Unsupported format conversion: ${inputFormat} -> ${outputFormat}`);
    }

    // 6. Upload output to R2
    const outputKey = `outputs/${jobId}/output.${outputFormat}`;
    const r2Url = await uploadFile(outputKey, outputPath, "application/octet-stream");

    // 7. Update job status to DONE
    await db.job.update({
      where: { id: jobId },
      data: {
        status: "DONE",
        outputUrl: r2Url,
      },
    });

    // Deduct credit and log
    const { userId } = job.data;
    if (userId) {
      await db.user.update({
        where: { id: userId },
        data: { credits: { decrement: 1 } }
      });
      await db.creditLog.create({
        data: { userId, amount: -1, reason: 'conversion', jobId: jobId }
      });
      await sendWebhook(userId, jobId, 'DONE', r2Url, undefined);
    }
  } catch (error) {
    // 9. On error: only mark as FAILED after all retries exhausted
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    const maxAttempts = job.opts.attempts || 3;
    if (job.attemptsMade >= maxAttempts - 1) {
      await db.job.update({
        where: { id: jobId },
        data: {
          status: "FAILED",
          error: errorMessage,
        },
      });
      if (job.data.userId) {
      await sendWebhook(job.data.userId, jobId, 'FAILED', undefined, errorMessage);
    }
    }
    throw error;
  } finally {
    // 8. Delete temp files
    try {
      const { unlinkSync, existsSync } = await import("fs");
      if (inputPath && existsSync(inputPath)) unlinkSync(inputPath);
      if (outputPath && existsSync(outputPath)) unlinkSync(outputPath);
      if (convertedPath && convertedPath !== outputPath && existsSync(convertedPath)) {
        unlinkSync(convertedPath);
      }
    } catch {
      // Ignore cleanup errors
    }
  }
}

const worker = new Worker<ConversionJobData>(
  "conversions",
  processJob,
  {
    connection: redisConnection,
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || '3'),
  }
);

worker.on("completed", (job) => {
  console.log(`Job ${job.id} completed successfully`);
});

worker.on("failed", async (job, err) => {
  console.error(`Job ${job?.id} failed with error: ${err.message}`);
  if (job && job.attemptsMade >= 3) {
    console.log(`Job ${job.id} exhausted all retries, marking as FAILED`);
  }
});

console.log("Worker started, listening for jobs...");
startCleanupCron();
