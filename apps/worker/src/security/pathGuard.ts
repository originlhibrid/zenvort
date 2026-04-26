/**
 * Shared path-safety helpers used by all converters.
 * Ensures files stay inside /tmp/zenvort/ — a dedicated subdirectory
 * that the worker owns and can audit/clean independently.
 */

import { resolve, join, sep } from "path";

// TMP_DIR supports env override for testing; defaults to /tmp/zenvort (Unix)
// or %TEMP%\zenvort on Windows when not running in Docker
const _TMP_DIR =
  process.env.TMP_DIR ??
  (process.platform === "win32"
    ? resolve(process.env.TEMP ?? "C:\\tmp", "zenvort")
    : "/tmp/zenvort");

export const TMP_DIR = resolve(_TMP_DIR);

/**
 * Resolves a path and asserts it is strictly under /tmp/zenvort/.
 * Throws on any traversal attempt or bare /tmp/ usage.
 */
export function sanitizeAndAssertTmpPath(p: string): string {
  const resolved = resolve(p);
  // Build a regex that matches TMP_DIR followed by the platform separator then any path.
  // Using a RegExp literal to avoid the double-escaping trap with "\\\\" in new RegExp(string).
  const re = sep === "\\"
    ? new RegExp(`^${TMP_DIR.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\\\.`)
    : new RegExp(`^${TMP_DIR}/`);
  if (!re.test(resolved)) {
    throw new Error(
      `Path traversal blocked: resolved path "${resolved}" is not under ${TMP_DIR}${sep === "\\" ? "\\" : "/"}`
    );
  }
  return resolved;
}

/** Build an input path for a job inside the safe directory. */
export function tmpInputPath(jobId: string, ext: string): string {
  return join(TMP_DIR, `${jobId}-input.${ext}`);
}

/** Build an output path for a job inside the safe directory. */
export function tmpOutputPath(jobId: string, ext: string): string {
  return join(TMP_DIR, `${jobId}-output.${ext}`);
}
