import "dotenv/config";
import { Worker, Job as BullJob } from "bullmq";
import ffmpeg from "fluent-ffmpeg";
import ffmpegInstaller from "@ffmpeg-installer/ffmpeg";
import { exec } from "child_process";
import { promisify } from "util";
import { pipeline } from "stream/promises";
import { createWriteStream, createReadStream, rmSync } from "fs";
import path from "path";
import tmp from "tmp";
import { db } from "@zenvort/db";
import { redisConnection, ConversionJobData } from "@zenvort/queue";
import { downloadFile, uploadFile } from "@zenvort/storage";

const execAsync = promisify(exec);

// Set ffmpeg path
ffmpeg.setFfmpegPath(ffmpegInstaller.path);

const VIDEO_AUDIO_FORMATS = ["mp4", "mp3", "mov", "avi", "wav", "webm", "mkv", "flac", "aac"];
const DOCUMENT_FORMATS = ["docx", "pdf", "pptx", "xlsx", "odt"];

async function processJob(job: BullJob<ConversionJobData>): Promise<void> {
  const { jobId, inputUrl, inputFormat, outputFormat } = job.data;
  const tempDir = tmp.dirSync({ prefix: "zenvort-" });
  let inputFilePath = "";
  let outputFilePath = "";

  try {
    // Update status to PROCESSING
    await db.job.update({
      where: { id: jobId },
      data: { status: "PROCESSING" },
    });

    // Download input file
    inputFilePath = path.join(tempDir.name, `input.${inputFormat}`);
    await downloadFile(inputUrl.replace(process.env.R2_PUBLIC_URL! + "/", ""), inputFilePath);

    outputFilePath = path.join(tempDir.name, `output.${outputFormat}`);

    // Process based on format type
    if (VIDEO_AUDIO_FORMATS.includes(inputFormat) || VIDEO_AUDIO_FORMATS.includes(outputFormat)) {
      // Use ffmpeg for video/audio
      await new Promise<void>((resolve, reject) => {
        ffmpeg(inputFilePath)
          .toFormat(outputFormat)
          .save(outputFilePath)
          .on("end", () => resolve())
          .on("error", (err) => reject(err));
      });
    } else if (DOCUMENT_FORMATS.includes(inputFormat)) {
      // Use libreoffice for documents
      const cmd = `libreoffice --headless --convert-to ${outputFormat} --outdir "${tempDir.name}" "${inputFilePath}"`;
      await execAsync(cmd);
      // LibreOffice renames the file
      const baseName = path.basename(inputFilePath, path.extname(inputFilePath));
      const convertedPath = path.join(tempDir.name, `${baseName}.${outputFormat}`);
      if (convertedPath !== outputFilePath) {
        await pipeline(createReadStream(convertedPath), createWriteStream(outputFilePath));
      }
    } else {
      throw new Error(`Unsupported format conversion: ${inputFormat} -> ${outputFormat}`);
    }

    // Upload output to R2
    const outputKey = `outputs/${jobId}/output.${outputFormat}`;
    const publicUrl = await uploadFile(outputKey, outputFilePath, "application/octet-stream");

    // Update job to DONE
    await db.job.update({
      where: { id: jobId },
      data: {
        status: "DONE",
        outputUrl: publicUrl,
      },
    });
  } catch (error) {
    // Update job to FAILED
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
    // Cleanup temp files
    try {
      rmSync(tempDir.name, { recursive: true, force: true });
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