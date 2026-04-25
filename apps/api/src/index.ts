import "dotenv/config";
import express, { Request, Response, NextFunction } from "express";
import multer from "multer";
import path from "path";
import crypto from "crypto";
import { db } from "@zenvort/db";
import { conversionsQueue, redisConnection } from "@zenvort/queue";
import { uploadFile } from "@zenvort/storage";

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.use(express.json());

// Auth middleware
const authMiddleware = async (req: Request, res: Response, next: NextFunction) => {
  const apiKey = req.headers.authorization?.replace("Bearer ", "");
  if (!apiKey) {
    res.status(401).json({ error: "Missing authorization header" });
    return;
  }

  const user = await db.user.findUnique({ where: { apiKey } });
  if (!user) {
    res.status(401).json({ error: "Invalid API key" });
    return;
  }

  (req as any).user = user;
  next();
};

// Error handler
const errorHandler = (err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).json({ error: err.message || "Internal server error" });
};

// Routes
app.get("/health", async (_req, res) => {
  try {
    // Check database connection
    await db.$connect();

    // Check Redis connection
    await new Promise((resolve, reject) => {
      redisConnection.ping((err, result) => {
        if (err) reject(err);
        else resolve(result);
      });
    });

    res.json({
      ok: true,
      timestamp: new Date().toISOString(),
      services: {
        redis: "connected",
        db: "connected",
      },
    });
  } catch (err) {
    res.status(503).json({
      ok: false,
      timestamp: new Date().toISOString(),
      services: {
        redis: "disconnected",
        db: "disconnected",
      },
    });
  }
});

app.post("/jobs", authMiddleware, upload.single("file"), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const file = req.file;
    if (!file) {
      res.status(400).json({ error: "No file uploaded" });
      return;
    }

    const { outputFormat } = req.body;
    if (!outputFormat) {
      res.status(400).json({ error: "outputFormat is required" });
      return;
    }

    const inputFormat = path.extname(file.originalname).slice(1).toLowerCase();
    if (!inputFormat) {
      res.status(400).json({ error: "Could not detect input format from file extension" });
      return;
    }

    const jobId = crypto.randomUUID();

    // Write buffer to temp file for upload since uploadFile expects a file path
    const tmpPath = `/tmp/${jobId}-${file.originalname}`;
    const { writeFileSync } = await import("fs");
    writeFileSync(tmpPath, file.buffer);

    // Upload file to R2
    const key = `inputs/${jobId}/${file.originalname}`;
    await uploadFile(key, tmpPath, file.mimetype);

    // Clean up temp file
    const { unlinkSync } = await import("fs");
    unlinkSync(tmpPath);

    // Get R2 URL for the uploaded file
    const r2Url = `${process.env.R2_PUBLIC_URL}/${key}`;

    // Create job in database
    const job = await db.job.create({
      data: {
        id: jobId,
        userId: (req as any).user.id,
        status: "PENDING",
        inputUrl: r2Url,
        inputFormat,
        outputFormat,
      },
    });

    // Queue conversion job
    await conversionsQueue.add("convert", {
      jobId: job.id,
      inputUrl: r2Url,
      inputFormat,
      outputFormat,
      userId: (req as any).user.id,
    });

    res.status(201).json({
      jobId: job.id,
      status: "PENDING",
      message: "Job queued successfully",
    });
  } catch (err) {
    next(err);
  }
});

app.get("/jobs/:id", authMiddleware, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const job = await db.job.findUnique({ where: { id: req.params.id } });
    if (!job) {
      res.status(404).json({ error: "Job not found" });
      return;
    }

    // Ensure user can only see their own jobs
    if (job.userId !== (req as any).user.id) {
      res.status(403).json({ error: "Access denied" });
      return;
    }

    res.json({
      id: job.id,
      status: job.status,
      inputFormat: job.inputFormat,
      outputFormat: job.outputFormat,
      inputUrl: job.inputUrl,
      outputUrl: job.outputUrl,
      error: job.error,
      createdAt: job.createdAt,
      updatedAt: job.updatedAt,
    });
  } catch (err) {
    next(err);
  }
});

app.post("/jobs/:id/webhook", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { status, outputUrl, error } = req.body;
    if (!status) {
      res.status(400).json({ error: "status is required" });
      return;
    }

    const job = await db.job.findUnique({ where: { id: req.params.id } });
    if (!job) {
      res.status(404).json({ error: "Job not found" });
      return;
    }

    await db.job.update({
      where: { id: req.params.id },
      data: {
        status,
        ...(outputUrl !== undefined && { outputUrl }),
        ...(error !== undefined && { error }),
      },
    });

    res.json({ ok: true });
  } catch (err) {
    next(err);
  }
});

app.use(errorHandler);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});
