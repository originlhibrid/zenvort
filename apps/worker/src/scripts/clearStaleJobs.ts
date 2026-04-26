import "dotenv/config";
import { Queue } from "bullmq";
import { redisConnection } from "@zenvort/queue";
import { db } from "@zenvort/db";

const conversionsQueue = new Queue("conversions", { connection: redisConnection });

async function main() {
  const cutoffArg = process.env.CUTOFF_DATE;
  if (!cutoffArg) {
    console.error("Error: CUTOFF_DATE env var is required (ISO-8601 format, e.g. 2026-04-01T00:00:00Z)");
    process.exit(1);
  }
  const cutoffDate = new Date(cutoffArg);
  if (isNaN(cutoffDate.getTime())) {
    console.error(`Error: CUTOFF_DATE "${cutoffArg}" is not a valid date`);
    process.exit(1);
  }

  console.log(`Draining conversions queue (jobs with createdBefore=${cutoffArg})...`);

  // Drain waiting jobs
  const waitingCount = await conversionsQueue.clean(0, 10000, "wait");
  // Drain delayed jobs
  const delayedCount = await conversionsQueue.clean(0, 10000, "delayed");
  // Drain failed jobs (clean up noise)
  const failedCount = await conversionsQueue.clean(0, 10000, "failed");

  const totalBullMq = [waitingCount, delayedCount, failedCount].reduce(
    (a, b) => a + (Array.isArray(b) ? b.length : 0), 0);

  console.log(`Removed BullMQ jobs — waiting: ${Array.isArray(waitingCount) ? waitingCount.length : 0}, delayed: ${Array.isArray(delayedCount) ? delayedCount.length : 0}, failed: ${Array.isArray(failedCount) ? failedCount.length : 0}`);

  // Update stale DB rows
  const result = await db.job.updateMany({
    where: {
      status: "PENDING",
      createdAt: { lt: cutoffDate },
    },
    data: {
      status: "FAILED",
      error: "Cleared: malformed inputFormat from pre-validation queue",
    },
  });
  console.log(`Updated ${result.count} DB Job rows to FAILED`);

  console.log("Done. Exiting cleanly.");
  process.exit(0);
}

main().catch((err) => {
  console.error("Script error:", err);
  process.exit(1);
});