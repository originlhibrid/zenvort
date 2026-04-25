import express, { Request, Response } from 'express';
import { db } from '@zenvort/db';

const router = express.Router();

// Admin auth middleware
async function requireAdmin(req: Request): Promise<any> {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw { status: 401, message: 'Missing API key' };
  }
  const apiKey = authHeader.split(' ')[1];
  const user = await db.user.findUnique({ where: { apiKey } });
  if (!user) throw { status: 401, message: 'Invalid API key' };
  if (user.role !== 'admin') throw { status: 403, message: 'Admin access required' };
  return user;
}

// GET /admin/stats
router.get('/stats', async (req: Request, res: Response) => {
  try {
    await requireAdmin(req);

    // Total users
    const totalUsers = await db.user.count();

    // Total jobs
    const totalJobs = await db.job.count();

    // Jobs today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const jobsToday = await db.job.count({
      where: { createdAt: { gte: today } }
    });

    // Active jobs (PENDING or PROCESSING)
    const activeJobs = await db.job.count({
      where: { status: { in: ['PENDING', 'PROCESSING'] } }
    });

    return res.json({
      totalUsers,
      totalJobs,
      jobsToday,
      activeJobs,
    });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /admin/users
router.get('/users', async (req: Request, res: Response) => {
  try {
    await requireAdmin(req);

    const page = parseInt(req.query.page as string) || 1;
    const limit = 20;
    const skip = (page - 1) * limit;

    const total = await db.user.count();

    const users = await db.user.findMany({
      orderBy: { createdAt: 'desc' },
      skip,
      take: limit,
      select: {
        id: true,
        email: true,
        credits: true,
        role: true,
        createdAt: true,
        _count: {
          select: { jobs: true }
        }
      }
    });

    return res.json({
      users,
      total,
      page,
      limit,
    });
  } catch (err: any) {
    if (err.status) return res.status(err.status).json({ error: err.message });
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// PATCH /admin/users/:id/credits
router.patch('/users/:id/credits', async (req: Request, res: Response) => {
  try {
    await requireAdmin(req);

    const { id } = req.params;
    const { amount } = req.body;

    if (typeof amount !== 'number') {
      return res.status(400).json({ error: 'Amount must be a number' });
    }

    const user = await db.user.findUnique({ where: { id } });
    if (!user) return res.status(404).json({ error: 'User not found' });

    // Calculate new credits
    const newCredits = user.credits + amount;
    if (newCredits < 0) {
      return res.status(400).json({ error: 'Credits cannot be negative' });
    }

    // Update user
    const updated = await db.user.update({
      where: { id },
      data: { credits: newCredits },
    });

    // Log the change
    await db.creditLog.create({
      data: {
        userId: id,
        amount,
        reason: amount > 0 ? 'manual_add' : 'manual_deduct',
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