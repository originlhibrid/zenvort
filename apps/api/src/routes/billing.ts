import express, { Request, Response } from 'express';
import crypto from 'crypto';
import Razorpay from 'razorpay';
import { db } from '@zenvort/db';

const router = express.Router();

const CREDIT_PACKS = {
  starter: { credits: 500, amount: 199, name: 'Starter Pack' },
  pro: { credits: 2000, amount: 599, name: 'Pro Pack' },
  enterprise: { credits: 10000, amount: 1999, name: 'Enterprise Pack' },
} as const;

type PackType = keyof typeof CREDIT_PACKS;

// Auth middleware helper
async function requireAuth(req: Request): Promise<any> {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw { status: 401, message: 'Missing API key' };
  }
  const apiKey = authHeader.split(' ')[1];
  const user = await db.user.findUnique({ where: { apiKey } });
  if (!user) throw { status: 401, message: 'Invalid API key' };
  return user;
}

// GET /billing/plans
router.get('/plans', (_req: Request, res: Response) => {
  const plans = Object.entries(CREDIT_PACKS).map(([key, pack]) => ({
    pack: key,
    credits: pack.credits,
    amount: pack.amount,
    currency: 'INR',
    name: pack.name,
  }));
  return res.json(plans);
});

// GET /billing/usage
router.get('/usage', async (req: Request, res: Response) => {
  try {
    const user = await requireAuth(req);

    // Total jobs
    const totalJobs = await db.job.count({ where: { userId: user.id } });

    // Jobs today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const jobsToday = await db.job.count({
      where: { userId: user.id, createdAt: { gte: today } }
    });

    // Done jobs count
    const doneJobs = await db.job.count({
      where: { userId: user.id, status: 'DONE' }
    });

    // Success rate
    const successRate = totalJobs > 0 ? Math.round((doneJobs / totalJobs) * 100) : 0;

    // Daily usage for last 30 days
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const jobs = await db.job.findMany({
      where: {
        userId: user.id,
        createdAt: { gte: thirtyDaysAgo }
      },
      select: { createdAt: true }
    });

    // Group by date
    const dailyMap = new Map<string, number>();
    for (const job of jobs) {
      const dateStr = job.createdAt.toISOString().split('T')[0];
      dailyMap.set(dateStr, (dailyMap.get(dateStr) || 0) + 1);
    }

    // Fill in missing dates with 0
    const dailyUsage = [];
    for (let i = 29; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      dailyUsage.push({ date: dateStr, count: dailyMap.get(dateStr) || 0 });
    }

    return res.json({
      credits: user.credits,
      totalJobs,
      jobsToday,
      successRate,
      dailyUsage,
    });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /billing/transactions
router.get('/transactions', async (req: Request, res: Response) => {
  try {
    const user = await requireAuth(req);

    const logs = await db.creditLog.findMany({
      where: { userId: user.id },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });

    return res.json({ logs });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /billing/orders
router.post('/orders', async (req: Request, res: Response) => {
  try {
    if (!process.env.RAZORPAY_KEY_ID) {
      return res.status(503).json({ error: 'Billing not configured' });
    }

    const user = await requireAuth(req);

    const { pack } = req.body as { pack: PackType };
    if (!pack || !CREDIT_PACKS[pack]) {
      return res.status(400).json({ error: 'Invalid pack' });
    }

    const creditPack = CREDIT_PACKS[pack];
    const razorpay = new Razorpay({
      key_id: process.env.RAZORPAY_KEY_ID,
      key_secret: process.env.RAZORPAY_KEY_SECRET,
    });

    const order = await razorpay.orders.create({
      amount: creditPack.amount * 100,
      currency: 'INR',
      receipt: `order_${user.id}_${Date.now()}`,
      notes: { userId: user.id, pack },
    });

    return res.json({
      orderId: order.id,
      amount: order.amount,
      currency: order.currency,
      credits: creditPack.credits,
    });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /billing/verify
router.post('/verify', async (req: Request, res: Response) => {
  try {
    const user = await requireAuth(req);

    const { orderId, paymentId, signature } = req.body;
    if (!orderId || !paymentId || !signature) {
      return res.status(400).json({ error: 'Missing verification fields' });
    }

    const generatedSignature = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET || '')
      .update(`${orderId}|${paymentId}`)
      .digest('hex');

    if (generatedSignature !== signature) {
      return res.status(400).json({ error: 'Invalid signature' });
    }

    const razorpay = new Razorpay({
      key_id: process.env.RAZORPAY_KEY_ID || '',
      key_secret: process.env.RAZORPAY_KEY_SECRET || '',
    });
    const order = await razorpay.orders.fetch(orderId);
    const pack = order.notes?.pack as PackType;
    const credits = CREDIT_PACKS[pack]?.credits || 500;

    const updated = await db.user.update({
      where: { id: user.id },
      data: { credits: { increment: credits } },
    });

    await db.creditLog.create({
      data: {
        userId: user.id,
        amount: credits,
        reason: 'purchase',
        jobId: orderId,
      },
    });

    return res.json({ ok: true, credits: updated.credits });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;