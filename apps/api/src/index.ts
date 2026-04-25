import "dotenv/config";
import express, { Request, Response, NextFunction } from "express";
import multer from "multer";
import path from "path";
import { db } from "@zenvort/db";
import { conversionsQueue } from "@zenvort/queue";
import { uploadFile } from "@zenvort/storage";
import { z } from "zod";

const app = express();
const upload = multer({ dest: "/tmp/uploads" });

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
app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/jobs", authMiddleware, upload.single("file"), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const file = req.file;
    if (!file) {
      res.status(400).json({ error: "No file uploaded" });
      return;
    }

    const bodySchema = z.object({
      outputFormat: z.string().min(1),
    });
    const { outputFormat } = bodySchema.parse(req.body);

    const inputFormat = path.extname(file.originalname).slice(1).toLowerCase();
    if (!inputFormat) {
      res.status(400).json({ error: "Could not detect input format from file extension" });
      return;
    }

    // Create job in database
    const job = await db.job.create({
      data: {
        userId: (req as any).user.id,
        status: "PENDING",
        inputUrl: "",
        inputFormat,
        outputFormat,
      },
    });

    // Upload file to R2
    const key = `inputs/${job.id}/${file.originalname}`;
    await uploadFile(key, file.path, file.mimetype);

    // Queue conversion job
    await conversionsQueue.add("convert", {
      jobId: job.id,
      inputUrl: `${process.env.R2_PUBLIC_URL}/${key}`,
      inputFormat,
      outputFormat,
      userId: (req as any).user.id,
    });

    res.status(201).json({ jobId: job.id, status: "PENDING" });
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
      outputUrl: job.outputUrl,
      error: job.error,
      createdAt: job.createdAt,
    });
  } catch (err) {
    next(err);
  }
});

app.use(errorHandler);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});