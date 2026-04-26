/**
 * In-memory conversion metrics — no external service required.
 * Reset on every worker restart (intentional: warm signals are fresher).
 *
 * Metrics tracked:
 *   conversionCount      — by { converterUsed, outputFormat }
 *   conversionFailureCount — by { converterUsed, errorType }
 *   averageDurationMs   — by converterUsed (running mean via Welford's algorithm)
 *   fallbackRate        — total: how often any fallback was used
 *   cacheHitCount       — jobs skipped via result caching
 */

export type ErrorType = "timeout" | "failed" | "unsupported";

// ── Welford's online algorithm for running mean and variance ───────────────────
class RunningStats {
  private n = 0;
  private mean = 0;
  private m2 = 0;

  update(value: number): number {
    this.n++;
    const delta = value - this.mean;
    this.mean += delta / this.n;
    const delta2 = value - this.mean;
    this.m2 += delta * delta2;
    return this.mean;
  }

  get count(): number {
    return this.n;
  }

  get average(): number {
    return this.n > 0 ? Math.round(this.mean) : 0;
  }
}

// ── Metric state ───────────────────────────────────────────────────────────────
const conversionCount = new Map<string, number>();
const conversionFailureCount = new Map<string, number>();
const averageDurationMsByConverter = new Map<string, RunningStats>();
const fallbackCountByRoute = new Map<string, number>();
const totalCountByRoute = new Map<string, number>();
let cacheHitCount = 0;

// ── Recording functions ───────────────────────────────────────────────────────

/**
 * Record a successful conversion.
 * @param converterUsed  The converter function name (fn.name)
 * @param outputFormat    Target output format
 * @param totalAttempts  Number of converters tried (including success)
 */
export function recordSuccess(
  converterUsed: string,
  outputFormat: string,
  totalAttempts: number,
  totalDurationMs: number
): void {
  const key = `${converterUsed}:${outputFormat}`;
  conversionCount.set(key, (conversionCount.get(key) ?? 0) + 1);

  const stats = averageDurationMsByConverter.get(converterUsed) ?? new RunningStats();
  stats.update(totalDurationMs);
  averageDurationMsByConverter.set(converterUsed, stats);
}

/**
 * Record a conversion failure.
 * @param converterUsed  The converter that failed
 * @param errorType      Classification of the failure
 */
export function recordFailure(converterUsed: string, errorType: ErrorType): void {
  const key = `${converterUsed}:${errorType}`;
  conversionFailureCount.set(key, (conversionFailureCount.get(key) ?? 0) + 1);
}

/**
 * Record whether a fallback was used for a given route.
 * Called once per job after all attempts are resolved.
 *
 * @param route           "inputFormat→outputFormat"
 * @param fallbackUsed    true if attempts > 1
 */
export function recordFallbackUsage(route: string, fallbackUsed: boolean): void {
  totalCountByRoute.set(route, (totalCountByRoute.get(route) ?? 0) + 1);
  if (fallbackUsed) {
    fallbackCountByRoute.set(route, (fallbackCountByRoute.get(route) ?? 0) + 1);
  }
}

/** Increment cache hit counter when a job is served from cache. */
export function recordCacheHit(): void {
  cacheHitCount++;
}

// ── Snapshot for HTTP export ───────────────────────────────────────────────────

export interface MetricsSnapshot {
  conversionCount: Record<string, number>;
  conversionFailureCount: Record<string, number>;
  averageDurationMs: Record<string, number>;
  fallbackRateByRoute: Record<string, { rate: number; total: number; fallbackCount: number }>;
  cacheHitCount: number;
  totalConversions: number;
  totalFailures: number;
}

export function getSnapshot(): MetricsSnapshot {
  const conversionCount_: Record<string, number> = {};
  conversionCount.forEach((v, k) => (conversionCount_[k] = v));

  const conversionFailureCount_: Record<string, number> = {};
  conversionFailureCount.forEach((v, k) => (conversionFailureCount_[k] = v));

  const averageDurationMs: Record<string, number> = {};
  averageDurationMsByConverter.forEach((stats, k) => {
    averageDurationMs[k] = stats.average;
  });

  const fallbackRateByRoute: Record<string, { rate: number; total: number; fallbackCount: number }> = {};
  totalCountByRoute.forEach((total, route) => {
    const fallbackCount = fallbackCountByRoute.get(route) ?? 0;
    fallbackRateByRoute[route] = {
      rate: total > 0 ? Math.round((fallbackCount / total) * 10000) / 100 : 0,
      total,
      fallbackCount,
    };
  });

  const totalConversions = Array.from(conversionCount.values()).reduce((a, b) => a + b, 0);
  const totalFailures = Array.from(conversionFailureCount.values()).reduce((a, b) => a + b, 0);

  return {
    conversionCount: conversionCount_,
    conversionFailureCount: conversionFailureCount_,
    averageDurationMs,
    fallbackRateByRoute,
    cacheHitCount,
    totalConversions,
    totalFailures,
  };
}
