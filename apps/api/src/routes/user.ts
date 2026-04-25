import express, { Request, Response } from 'express';
import { db } from '@zenvort/db';

const router = express.Router();

// PATCH /user/webhook
router.patch('/webhook', async (req: Request, res: Response) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Missing API key' });
    }
    const apiKey = authHeader.split(' ')[1];
    const user = await db.user.findUnique({ where: { apiKey } });
    if (!user) return res.status(401).json({ error: 'Invalid API key' });

    const { webhookUrl } = req.body;
    if (!webhookUrl) {
      return res.status(400).json({ error: 'webhookUrl is required' });
    }

    try {
      new URL(webhookUrl);
    } catch {
      return res.status(400).json({ error: 'Invalid URL format' });
    }

    const updated = await db.user.update({
      where: { id: user.id },
      data: { webhookUrl },
    });

    return res.json({ ok: true, webhookUrl: updated.webhookUrl });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
