import express, { Request, Response, NextFunction } from 'express'
import multer from 'multer'
import crypto from 'crypto'
import { db } from '@zenvort/db'
import { conversionsQueue } from '@zenvort/queue'
import { uploadFile } from '@zenvort/storage'
import path from 'path'
import fs from 'fs/promises'
import os from 'os'

declare global {
  namespace Express {
    interface Request {
      user?: any
    }
  }
}

const router = express.Router()
const upload = multer({ storage: multer.memoryStorage() })

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

// POST /jobs
router.post('/', requireApiKey, upload.single('file'), async (req: Request, res: Response) => {
  try {
    const { outputFormat } = req.body
    const file = req.file

    if (!file) return res.status(400).json({ error: 'No file uploaded' })
    if (!outputFormat) return res.status(400).json({ error: 'outputFormat is required' })

    const jobId = crypto.randomUUID()
    const ext = path.extname(file.originalname).replace('.', '').toLowerCase()
    const inputFormat = ext

    // Write buffer to temp file then upload
    const tempPath = path.join(os.tmpdir(), file.originalname)
    await fs.writeFile(tempPath, file.buffer)

    const storageKey = `inputs/${jobId}/${file.originalname}`
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
    return res.json(job)
  } catch (err) {
    console.error(err)
    return res.status(500).json({ error: 'Internal server error' })
  }
})

export default router
