/**
 * /tmp/zenvort/ orphan cleanup + metrics HTTP server.
 *
 * Cleanup job: runs every 10 minutes via setInterval.
 * Deletes files in /tmp/zenvort/ older than 30 minutes that were not
 * already cleaned up (orphaned files from crashed/stale jobs).
 *
 * Metrics server: internal Express on port 3001.
 * Not exposed publicly — internal ops only.
 */

import express from "express";
import cron from "node-cron";
import { readdirSync, statSync, unlinkSync } from "fs";
import { join } from "path";
import { getSnapshot } from "./metrics.js";
import { TMP_DIR } from "./security/pathGuard.js";

const METRICS_PORT = 3001;
const ORPHAN_MAX_AGE_MS = 30 * 60 * 1000;  // 30 minutes
const CLEANUP_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

// ── Metrics HTTP server (internal only) ─────────────────────────────────────
export function startMetricsServer(): void {
  const app = express();
  app.get("/metrics", (_req, res) => {
    res.json(getSnapshot());
  });
  app.get("/health", (_req, res) => {
    res.json({ ok: true, ts: new Date().toISOString() });
  });

  app.listen(METRICS_PORT, () => {
    console.log(`[worker] Metrics server listening on :${METRICS_PORT}`);
  });
}

// ── Orphan file cleanup scheduler ─────────────────────────────────────────────
export function startOrphanCleanup(): void {
  setInterval(() => {
    const deleted = cleanupOrphanedFiles();
    if (deleted > 0) {
      console.log(`[worker] Orphan cleanup: deleted ${deleted} stale file(s)`);
    }
  }, CLEANUP_INTERVAL_MS);

  console.log(
    `[worker] Orphan cleanup scheduled every ${CLEANUP_INTERVAL_MS / 1000 / 60} minutes ` +
    `(max age: ${ORPHAN_MAX_AGE_MS / 1000 / 60} minutes)`
  );
}

function cleanupOrphanedFiles(): number {
  let deleted = 0;
  const now = Date.now();

  try {
    const entries = readdirSync(TMP_DIR);
    for (const entry of entries) {
      const fullPath = join(TMP_DIR, entry);
      try {
        const s = statSync(fullPath);
        if (!s.isFile()) continue;
        const ageMs = now - s.mtimeMs;
        if (ageMs > ORPHAN_MAX_AGE_MS) {
          unlinkSync(fullPath);
          deleted++;
        }
      } catch {
        // Skip entries we can't stat (race, permissions)
      }
    }
  } catch {
    // Directory missing or empty — nothing to clean
  }

  return deleted;
}
