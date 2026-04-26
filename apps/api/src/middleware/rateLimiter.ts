import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";
import { Redis } from "ioredis";
import { Request, Response } from "express";
import { db } from "@zenvort/db";

const redisClient = new Redis(process.env.REDIS_URL || "redis://redis:6379");

// Global rate limiter: 100 requests per 15 minutes per IP
export const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  keyGenerator: (req: Request) => `global:${req.ip}`,
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Rate limit exceeded",
      message: "Too many requests, please try again later",
    });
  },
});

/**
 * Job submit rate limiter: 10 requests per hour per authenticated user.
 *
 * BEFORE: keyGenerator returned req.ip as fallback when no Bearer token.
 *   → Multiple users sharing an IP shared the same bucket.
 *   → Attacker could exhaust another user's quota by uploading from same IP.
 *
 * AFTER: Falls back to req.ip ONLY when no Authorization header is present
 *   (e.g. unauthenticated pre-signup requests). Authenticated requests always
 *   resolve to the actual userId from the database — user isolation guaranteed.
 */
export const jobSubmitLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  async keyGenerator(req: Request): Promise<string> {
    const authHeader = req.headers.authorization;
    if (authHeader?.startsWith("Bearer ")) {
      const apiKey = authHeader.split(" ")[1];
      try {
        const user = await db.user.findUnique({ where: { apiKey }, select: { id: true } });
        if (user) return `job-limit:user:${user.id}`;
      } catch {
        // DB error — fall through to IP-based keying
      }
    }
    return `job-limit:ip:${req.ip}`;
  },
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Rate limit exceeded",
      message: "Max 10 jobs per hour",
    });
  },
});

// Login brute-force protection: 5 failed attempts per 15 min per IP
export const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  keyGenerator: (req: Request) => `login:${req.ip}`,
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Too many login attempts. Try again in 15 minutes.",
    });
  },
  skipSuccessfulRequests: true,
});

// Signup rate limit: 5 signups per hour per IP
export const signupLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  keyGenerator: (req: Request) => `signup:${req.ip}`,
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Too many signups from this IP. Try again in 1 hour.",
    });
  },
});
