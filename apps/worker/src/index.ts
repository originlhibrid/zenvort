import "dotenv/config";
import { Worker, Job as BullJob } from "bullmq";
import path from "path";
import { stat } from "fs/promises";
import { mkdir } from "fs/promises";
import sharp from "sharp";
import { db } from "@zenvort/db";
import { redisConnection, ConversionJobData } from "@zenvort/queue";
import { downloadFile, uploadFile } from "@zenvort/storage";
import { executeConversion } from "./executor.js";
import { TMP_DIR } from "./security/pathGuard.js";
import { acquireSemaphore, releaseSemaphore, checkDiskSpace } from "./security/semaphore.js";
import { assertMimeTypeMatches } from "./security/mimeGuard.js";
import { startOrphanCleanup, startMetricsServer } from "./cleanup.js";
import {
  recordSuccess,
  recordFailure,
  recordFallbackUsage,
  recordCacheHit,
  type ErrorType,
} from "./metrics.js";

const MAX_INPUT_BYTES = 200 * 1024 * 1024;
const MAX_OUTPUT_BYTES = 500 * 1024 * 1024;
const LOG = (jobId: string) => `[worker][${jobId}]`;

// ── Bootstrap ────────────────────────────────────────────────────────────────────
mkdir(TMP_DIR, { recursive: true }).catch((err) =>
  console.error(`[worker] Failed to create ${TMP_DIR}:`, err)
);

// Sharp: limit to 1 thread to prevent libvips from competing with other converters
sharp.concurrency(1);

// Start internal services
startOrphanCleanup();
startMetricsServer();

async function sendWebhook(
  userId: string,
  jobId: string,
  status: "DONE" | "FAILED",
  outputUrl: string | undefined,
  error: string | undefined
): Promise<void> {
  try {
    const user = await db.user.findUnique({ where: { id: userId } });
    if (!user?.webhookUrl) return;

    const response = await fetch(user.webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId, status, outputUrl, error, timestamp: new Date().toISOString() }),
    });

    if (response.ok) {
      console.log(`${LOG(jobId)} Webhook delivered to ${user.webhookUrl}`);
    } else {
      console.error(`${LOG(jobId)} Webhook failed: ${response.status}`);
    }
  } catch (err) {
    console.error(`${LOG(jobId)} Webhook error:`, err);
  }
}

async function deleteIfExists(filePath: string): Promise<void> {
  try {
    const { unlinkSync, existsSync } = await import("fs");
    if (filePath && existsSync(filePath)) unlinkSync(filePath);
  } catch {
    // Ignore cleanup errors
  }
}

async function processJob(job: BullJob<ConversionJobData>): Promise<void> {
  const { jobId, inputUrl, inputFormat, outputFormat } = job.data;
  const userId = job.data.userId;

  let inputPath = "";
  let outputPath = "";

  // ── Guard: reject self-conversion ─────────────────────────────────────────
  if (inputFormat === outputFormat) {
    const errMsg = "Invalid job data: inputFormat equals outputFormat";
    await db.job.update({ where: { id: jobId }, data: { status: "FAILED", error: errMsg } });
    if (userId) await sendWebhook(userId, jobId, "FAILED", undefined, errMsg);
    throw Object.assign(new Error(errMsg), { unrecoverable: true });
  }

  console.log(`${LOG(jobId)} Job received`, { jobId, inputFormat, outputFormat, userId });

  try {
    // ── 1. Acquire concurrency slot ───────────────────────────────────────────
    await acquireSemaphore();

    // ── 2. Check disk space before accepting the job ─────────────────────────
    await checkDiskSpace();

    // ── 3. Cache lookup: reuse existing DONE output for identical inputs ─────
    const cached = await db.job.findFirst({
      where: {
        inputUrl,
        outputFormat,
        status: "DONE",
        outputUrl: { not: null },
      },
      select: { outputUrl: true },
      orderBy: { createdAt: "desc" },
    });

    if (cached?.outputUrl) {
      recordCacheHit();
      console.log(`${LOG(jobId)} Cache hit — reusing ${cached.outputUrl}`);

      await db.job.update({
        where: { id: jobId },
        data: { status: "DONE", outputUrl: cached.outputUrl },
      });

      if (userId) {
        await sendWebhook(userId, jobId, "DONE", cached.outputUrl, undefined);
      }
      return;
    }

    // ── 4. Update job status to PROCESSING ─────────────────────────────────
    await db.job.update({ where: { id: jobId }, data: { status: "PROCESSING" } });

    // ── 5. Download input file from R2 ───────────────────────────────────────
    const inputKey = inputUrl.replace(`${process.env.R2_PUBLIC_URL}/`, "");
    const urlPathSegment = inputUrl.split("/").pop() ?? "";
    const rawExt = path.extname(urlPathSegment).replace(/^\./, "");
    const actualExt = rawExt || inputFormat;

    inputPath = `${TMP_DIR}/${jobId}-input.${actualExt}`;
    outputPath = `${TMP_DIR}/${jobId}-output.${outputFormat}`;

    await downloadFile(inputKey, inputPath);

    // ── 6. Validate downloaded file size (200 MB limit) ──────────────────────
    const inputStat = await stat(inputPath);
    if (inputStat.size > MAX_INPUT_BYTES) {
      throw Object.assign(
        new Error(`Input file exceeds 200MB limit: ${inputStat.size} bytes`),
        { unrecoverable: true }
      );
    }

    // ── 7. Route lookup + structured log ───────────────────────────────────
    const { getRoute } = await import("./routes.js");
    const routeEntry = getRoute(inputFormat, outputFormat);

    console.log(`${LOG(jobId)} Conversion started`, {
      jobId,
      routeFound: routeEntry !== null,
      converterCount: routeEntry ? routeEntry.converters.length : 0,
    });

    // ── 8. Execute the fallback conversion chain ───────────────────────────────
    const { converterUsed, attempts } = await executeConversion(
      jobId,
      inputPath,
      outputPath,
      inputFormat,
      outputFormat
    );

    const totalDurationMs = attempts.reduce((sum, a) => sum + a.durationMs, 0);

    console.log(`${LOG(jobId)} Conversion done`, { jobId, converterUsed, totalDurationMs, attempts });

    // ── 9. Validate output file size before upload (500 MB limit) ───────────
    const outputStat = await stat(outputPath);
    if (outputStat.size > MAX_OUTPUT_BYTES) {
      await deleteIfExists(outputPath);
      throw Object.assign(
        new Error(`Output file exceeds 500MB limit: ${outputStat.size} bytes`),
        { unrecoverable: true }
      );
    }

    // ── 10. MIME type validation before R2 upload ──────────────────────────
    await assertMimeTypeMatches(outputPath, outputFormat, jobId);

    // ── 11. Upload output to R2 ────────────────────────────────────────────
    const outputKey = `outputs/${jobId}/output.${outputFormat}`;
    const r2Url = await uploadFile(outputKey, outputPath, "application/octet-stream");

    // ── 12. Delete temp files immediately after successful upload ──────────
    await deleteIfExists(inputPath);
    await deleteIfExists(outputPath);

    // ── 13. Update job to DONE with converter metadata ─────────────────────
    await db.job.update({
      where: { id: jobId },
      data: { status: "DONE", outputUrl: r2Url, converterUsed },
    });

    // ── 14. Record metrics ──────────────────────────────────────────────────
    const fallbackUsed = attempts.length > 1;
    recordSuccess(converterUsed, outputFormat, attempts.length, totalDurationMs);
    recordFallbackUsage(`${inputFormat}→${outputFormat}`, fallbackUsed);

    // ── 15. Deduct credit and log ───────────────────────────────────────────
    if (userId) {
      await db.user.update({ where: { id: userId }, data: { credits: { decrement: 1 } } });
      await db.creditLog.create({ data: { userId, amount: -1, reason: "conversion", jobId } });
      await sendWebhook(userId, jobId, "DONE", r2Url, undefined);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    const isUnrecoverable =
      error instanceof Error && (error as { unrecoverable?: boolean }).unrecoverable === true;
    const isRetryable =
      error instanceof Error && (error as { retryable?: boolean }).retryable === true;

    // ── Classify failure and record metric ──────────────────────────────────
    let errorType: ErrorType = "failed";
    if (isTimeoutError(error)) errorType = "timeout";
    if (errorMessage.includes("No conversion route")) errorType = "unsupported";

    const maxAttempts = job.opts.attempts ?? 3;

    console.error(`${LOG(jobId)} Job failed`, {
      jobId,
      error: errorMessage,
      attemptsMade: job.attemptsMade,
      maxAttempts,
      isUnrecoverable,
      isRetryable,
    });

    // Mark FAILED only on the final attempt OR unrecoverable errors.
    // Skip for retryable errors (disk space, capacity) — let BullMQ re-queue.
    const isLastAttempt = job.attemptsMade >= maxAttempts - 1;
    if ((isLastAttempt || isUnrecoverable) && !isRetryable) {
      await db.job.update({ where: { id: jobId }, data: { status: "FAILED", error: errorMessage } });
      if (userId) await sendWebhook(userId, jobId, "FAILED", undefined, errorMessage);
      recordFailure(errorMessage.split(":")[0] ?? "unknown", errorType);
    }

    if (isUnrecoverable) {
      throw Object.assign(new Error(errorMessage), { unrecoverable: true });
    }
    throw error;
  } finally {
    releaseSemaphore();
    await deleteIfExists(inputPath);
    await deleteIfExists(outputPath);
  }
}

// ── Timeout classifier used for metrics ────────────────────────────────────────
function isTimeoutError(err: unknown): boolean {
  return err instanceof Error && /timed out/i.test(err.message);
}

const worker = new Worker<ConversionJobData>(
  "conversions",
  processJob,
  {
    connection: redisConnection,
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || "3"),
    lockDuration: 10 * 60 * 1000,
    lockRenewTime: 60_000,
  }
);

worker.on("completed", (job) => {
  console.log(`${LOG(job.id ?? "?")} Completed successfully`);
});

worker.on("failed", async (job, err) => {
  console.error(`${LOG(job?.id ?? "?")} Failed: ${err.message}`);
});

console.log("Worker started, listening for jobs...");
