import express from 'express';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import { db } from '@zenvort/db';
import { loginLimiter, signupLimiter } from '../middleware/rateLimiter.js';

const router = express.Router();

// POST /auth/signup
router.post('/signup', signupLimiter, async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validate input
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    // Validate password length
    if (password.length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters' });
    }

    // Check if user already exists
    const existing = await db.user.findUnique({ where: { email } });
    if (existing) {
      return res.status(409).json({ error: 'Email already registered' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Generate API key
    const apiKey = crypto.randomUUID();

    // Create user
    const user = await db.user.create({
      data: {
        email,
        password: hashedPassword,
        apiKey,
        credits: 100,
        role: 'user',
      },
    });

    // Create signup credit log
    await db.creditLog.create({
      data: {
        userId: user.id,
        amount: 100,
        reason: 'signup',
      },
    });

    return res.status(201).json({
      apiKey,
      user: {
        id: user.id,
        email: user.email,
        credits: user.credits,
        role: user.role,
      },
    });
  } catch (err) {
    console.error('Signup error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /auth/login
router.post('/login', loginLimiter, async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }

    // Find user by email
    const user = await db.user.findUnique({ where: { email } });
    if (!user) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    // Check if password is set (legacy users may not have password)
    if (!user.password) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    // Verify password
    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    return res.json({
      apiKey: user.apiKey,
      user: {
        id: user.id,
        email: user.email,
        credits: user.credits,
        role: user.role,
        webhookUrl: user.webhookUrl,
      },
    });
  } catch (err) {
    console.error('Login error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;