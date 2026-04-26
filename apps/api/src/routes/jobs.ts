import express, { Request, Response, NextFunction } from 'express'
import multer from 'multer'
import crypto from 'crypto'
import { db } from '@zenvort/db'
import { conversionsQueue } from '@zenvort/queue'
import { uploadFile } from '@zenvort/storage'
import { getSupportedFormats } from '@zenvort/shared'
import path from 'path'
import fs from 'fs/promises'
import os from 'os'
import { jobSubmitLimiter } from '../middleware/rateLimiter.js'

const { inputFormats: VALID_INPUT_FORMATS, outputFormats: VALID_OUTPUT_FORMATS } = getSupportedFormats()
const INPUT_SET = new Set(VALID_INPUT_FORMATS)
const OUTPUT_SET = new Set(VALID_OUTPUT_FORMATS)

declare global {
  namespace Express {
    interface Request {
      user?: any
    }
  }
}

const router = express.Router()
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB max
    files: 1, // only 1 file per request
  },
})

// Auth middleware
async function requireApiKey(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing API key' })
  }
  const apiKey = authHeader.split(' ')[1]
  const user = await db.user.findUnique({ where: { apiKey } })
  if (!user) return res.status(401).json({ error: 'Invalid API key' })
  req.user = user
  next()
}

// GET /jobs - List user's jobs with pagination
router.get('/', requireApiKey, async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 20;
    const skip = (page - 1) * limit;

    // Count total jobs for this user
    const total = await db.job.count({
      where: { userId: req.user.id }
    });

    // Get paginated jobs, newest first
    const jobs = await db.job.findMany({
      where: { userId: req.user.id },
      orderBy: { createdAt: 'desc' },
      skip,
      take: limit,
    });

    return res.json({
      jobs,
      total,
      page,
      limit,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /jobs
router.post('/',
  jobSubmitLimiter,
  requireApiKey,
  (req, res, next) => {
    upload.single('file')(req, res, (err) => {
      if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          return res.status(413).json({ error: 'File too large. Maximum size is 100MB.' })
        }
        return res.status(400).json({ error: err.message })
      }
      if (err) return res.status(500).json({ error: 'Upload failed' })
      next()
    })
  },
  async (req: Request, res: Response) => {
  try {
    const { outputFormat } = req.body
    const file = req.file

    if (!file) return res.status(400).json({ error: 'No file uploaded' })
    if (!outputFormat) return res.status(400).json({ error: 'outputFormat is required' })

    // Validate input format (extension-based)
    const ext = path.extname(file.originalname).replace('.', '').toLowerCase()
    if (!INPUT_SET.has(ext)) {
      return res.status(400).json({ error: `Unsupported input format: ${ext}` })
    }

    // Validate output format against whitelist
    if (!OUTPUT_SET.has(outputFormat.toLowerCase())) {
      return res.status(400).json({ error: `Unsupported output format: ${outputFormat}` })
    }

    // Check credits
    if (req.user.credits <= 0) {
      return res.status(402).json({ error: 'Insufficient credits' })
    }

    const jobId = crypto.randomUUID()
    const inputFormat = ext

    // Sanitize filename to prevent path traversal
    const safeName = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_')
    const tempPath = path.join(os.tmpdir(), `${jobId}-${safeName}`)

    // Write buffer to temp file then upload
    await fs.writeFile(tempPath, file.buffer)

    const storageKey = `inputs/${jobId}/${safeName}`
    const inputUrl = await uploadFile(storageKey, tempPath, file.mimetype)

    await fs.unlink(tempPath)

    // Create job in DB
    const job = await db.job.create({
      data: {
        id: jobId,
        userId: req.user.id,
        status: 'PENDING',
        inputUrl,
        inputFormat,
        outputFormat,
      }
    })

    // Push to queue
    await conversionsQueue.add('convert', {
      jobId,
      inputUrl,
      inputFormat,
      outputFormat,
      userId: req.user.id
    })

    return res.status(201).json({
      jobId: job.id,
      status: job.status,
      message: 'Job queued successfully'
    })
  } catch (err) {
    console.error(err)
    return res.status(500).json({ error: 'Internal server error' })
  }
})

// GET /jobs/:id
router.get('/:id', requireApiKey, async (req: Request, res: Response) => {
  try {
    const job = await db.job.findUnique({ where: { id: req.params.id } })
    if (!job) return res.status(404).json({ error: 'Job not found' })
    if (job.userId !== req.user.id) {
      return res.status(403).json({ error: 'Access denied' })
    }
    return res.json({ ...job, credits: req.user.credits })
  } catch (err) {
    console.error(err)
    return res.status(500).json({ error: 'Internal server error' })
  }
})

export default router