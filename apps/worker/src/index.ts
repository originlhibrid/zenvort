import "dotenv/config";
import { Worker, Job as BullJob } from "bullmq";
import ffmpeg from "fluent-ffmpeg";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { db } from "@zenvort/db";
import { redisConnection, ConversionJobData } from "@zenvort/queue";
import { downloadFile, uploadFile } from "@zenvort/storage";

const execAsync = promisify(exec);

const VIDEO_AUDIO_FORMATS = ["mp4", "mov", "avi", "mkv", "webm", "mp3", "wav", "aac", "flac"];
const libreOfficeFormats = ['pdf', 'docx', 'doc', 'pptx', 'xlsx', 'odt', 'html', 'txt'];

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
  } catch (error) {
    // 9. On error: update status to FAILED
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    await db.job.update({
      where: { id: jobId },
      data: {
        status: "FAILED",
        error: errorMessage,
      },
    });
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
    concurrency: 3,
  }
);

worker.on("completed", (job) => {
  console.log(`Job ${job.id} completed`);
});

worker.on("failed", (job, err) => {
  console.error(`Job ${job?.id} failed:`, err.message);
});

console.log("Worker started, listening for jobs...");
