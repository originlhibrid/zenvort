/**
 * LibreOffice per-process mutex.
 *
 * LibreOffice cannot run multiple instances simultaneously with the same
 * user profile — it will refuse to start or corrupt its lock file.
 *
 * This module exports an async mutex that serializes all LibreOffice
 * conversions, even when BullMQ concurrency > 1.
 *
 * Usage:
 *   await libreofficeMutex.run(async () => {
 *     await convert(..., inputPath, outputPath, ...);
 *   });
 */

import { Mutex } from "async-mutex";

export const libreofficeMutex = new Mutex();

export { Mutex };

/** Alias for the public API — run a callback while holding the mutex. */
libreofficeMutex.runExclusive; // no-op export alias for IDE hints
