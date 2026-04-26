/**
 * Concurrency semaphore and disk-space guard.
 *
 * - acquireSemaphore / releaseSemaphore: module-level counter that enforces
 *   WORKER_CONCURRENCY limit at the conversion level too, not just BullMQ concurrency.
 *
 * - checkDiskSpace: reads /tmp/zenvort/ total size via `du -sb`.
 *   Throws a RETRYABLE error if over 2 GB so BullMQ re-queues the job.
 */

import { exec } from "child_process";
import { promisify } from "util";
import { TMP_DIR } from "./pathGuard.js";

const execAsync = promisify(exec);
const MAX_TMP_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB

let activeConversions = 0;
const MAX_CONCURRENT = parseInt(process.env.WORKER_CONCURRENCY || "3");

export async function acquireSemaphore(): Promise<void> {
  if (activeConversions >= MAX_CONCURRENT) {
    throw Object.assign(
      new Error(
        `Worker at max capacity (${MAX_CONCURRENT} concurrent conversions). Retrying later.`
      ),
      { retryable: true }
    );
  }
  activeConversions++;
}

export function releaseSemaphore(): void {
  activeConversions = Math.max(0, activeConversions - 1);
}

export async function checkDiskSpace(): Promise<void> {
  try {
    const { stdout } = await execAsync(
      `du -sb ${TMP_DIR} 2>/dev/null | awk '{print $1}'`,
      { timeout: 10_000 }
    );
    const bytes = parseInt(stdout.trim(), 10);
    if (isNaN(bytes)) return;
    if (bytes > MAX_TMP_BYTES) {
      throw Object.assign(
        new Error(
          `/tmp/zenvort/ exceeds ${(MAX_TMP_BYTES / 1024 / 1024 / 1024).toFixed(1)}GB limit (${bytes} bytes used). Retrying later.`
        ),
        { retryable: true }
      );
    }
  } catch (err) {
    if (err instanceof Error && (err as NodeJS.ErrnoException).code === "ENOENT") {
      return; // Directory doesn't exist yet — not an error
    }
    if (err instanceof Error && (err as { retryable?: boolean }).retryable) {
      throw err;
    }
    console.error("[diskSpaceCheck] Unexpected error:", err);
  }
}
