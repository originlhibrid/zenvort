import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import jobsRouter from "./routes/jobs.js";
import userRouter from "./routes/user.js";
import billingRouter from "./routes/billing.js";
import authRouter from "./routes/auth.js";
import adminRouter from "./routes/admin.js";
import { globalLimiter } from "./middleware/rateLimiter.js";

const app = express();

app.use(helmet({
  crossOriginResourcePolicy: { policy: "cross-origin" },
}));

const allowedOrigins = [
  process.env.ALLOWED_ORIGIN,
  "http://localhost:5173",
  "http://localhost:4173",
  "http://localhost:3000",
].filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    if (!origin) return callback(null, true);
    if (allowedOrigins.includes(origin)) return callback(null, true);
    return callback(new Error("Not allowed by CORS"));
  },
  credentials: false,
  methods: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(globalLimiter);

app.get('/health', (req, res) => {
  res.json({ ok: true, timestamp: new Date().toISOString() })
})

app.use('/auth', authRouter);
app.use('/jobs', jobsRouter);
app.use('/user', userRouter);
app.use('/billing', billingRouter);
app.use('/admin', adminRouter);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});