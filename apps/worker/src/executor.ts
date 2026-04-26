import { existsSync } from "fs";
import { getRoute } from "./routes.js";
import type { ConversionRoute } from "@zenvort/shared";

export type AttemptResult = {
  converter: string;
  success: boolean;
  durationMs: number;
  error?: string;
};

/**
 * Returns true if the error is a timeout error (Converter timed out).
 */
export function isTimeoutError(err: unknown): boolean {
  if (err instanceof Error) {
    return (
      err.message.includes("timed out") ||
      err.message.includes("timed out after")
    );
  }
  return false;
}

/**
 * Executes the fallback conversion chain for a job.
 *
 * @returns { converterUsed, attempts } on success
 * @throws Aggregated error if all converters fail
 */
export async function executeConversion(
  jobId: string,
  inputPath: string,
  outputPath: string,
  inputFormat: string,
  outputFormat: string
): Promise<{ converterUsed: string; attempts: AttemptResult[] }> {
  // ── Security checks ─────────────────────────────────────────────────────────
  const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!UUID_REGEX.test(jobId)) {
    throw new Error(`executeConversion: jobId is not a valid UUID: ${jobId}`);
  }

  // Paths are validated by sanitizeAndAssertTmpPath() inside each converter (cross-platform).
  const resolvedInput  = inputPath;
  const resolvedOutput = outputPath;

  // ── Route lookup ───────────────────────────────────────────────────────────
  const route: ConversionRoute | null = getRoute(inputFormat, outputFormat);
  if (!route) {
    throw new Error(
      `No conversion route for ${inputFormat}→${outputFormat}`
    );
  }

  const { converters, description } = route;
  const attempts: AttemptResult[] = [];

  console.log(
    `[${jobId}] Starting ${description} (${converters.length} converter(s))`
  );

  // ── Fallback chain ─────────────────────────────────────────────────────────
  for (let i = 0; i < converters.length; i++) {
    const converterFn = converters[i];
    const converterName = converterFn.name || "anonymous";

    console.log(
      `[${jobId}] Attempt ${i + 1}/${converters.length} — ${converterName}`
    );

    // Clean slate before each attempt
    if (existsSync(resolvedOutput)) {
      try {
        await import("fs").then((fs) => fs.promises.unlink(resolvedOutput));
      } catch {
        // Ignore cleanup errors — may not exist
      }
    }

    const start = performance.now();

    try {
      await converterFn(resolvedInput, resolvedOutput, inputFormat, outputFormat);

      const durationMs = Math.round(performance.now() - start);

      console.log(
        `[${jobId}] ${converterName} succeeded in ${durationMs}ms`
      );

      attempts.push({
        converter: converterName,
        success: true,
        durationMs,
      });

      return { converterUsed: converterName, attempts };
    } catch (err) {
      const durationMs = Math.round(performance.now() - start);
      const isTimeout = isTimeoutError(err);
      const errorMsg = err instanceof Error ? err.message : String(err);

      if (isTimeout) {
        console.log(`[${jobId}] ${converterName} timed out after ${durationMs}ms`);
      } else {
        console.log(`[${jobId}] ${converterName} failed: ${errorMsg}`);
      }

      attempts.push({
        converter: converterName,
        success: false,
        durationMs,
        error: errorMsg,
      });

      // If last converter failed, the aggregated error is thrown below
    }
  }

  // ── All converters failed ─────────────────────────────────────────────────
  const errors = attempts
    .map((a) => `  - ${a.converter}: ${a.error ?? "unknown error"}`)
    .join("\n");

  throw new Error(
    `All converters failed for ${inputFormat}→${outputFormat}:\n${errors}`
  );
}
