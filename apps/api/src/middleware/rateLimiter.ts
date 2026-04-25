import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";
import { Redis } from "ioredis";
import { Request, Response } from "express";

const redisClient = new Redis(process.env.REDIS_URL || "redis://redis:6379");

// Global rate limiter: 100 requests per 15 minutes per IP
export const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Rate limit exceeded",
      message: "Too many requests, please try again later",
    });
  },
});

// Job submit rate limiter: 10 requests per hour per user
export const jobSubmitLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => (redisClient as any).call(...args),
  }),
  keyGenerator: (req: Request) => {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith("Bearer ")) {
      return `job-limit:${authHeader.split(" ")[1]}`;
    }
    return `job-limit:${req.ip}`;
  },
  handler: (_req: Request, res: Response) => {
    res.status(429).json({
      error: "Rate limit exceeded",
      message: "Max 10 jobs per hour on free tier",
    });
  },
});
