import "dotenv/config";
import express from "express";
import jobsRouter from "./routes/jobs.js";
import userRouter from "./routes/user.js";
import billingRouter from "./routes/billing.js";
import { globalLimiter } from "./middleware/rateLimiter.js";

const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(globalLimiter);

app.get('/health', (req, res) => {
  res.json({ ok: true, timestamp: new Date().toISOString() })
})

app.use('/jobs', jobsRouter);
app.use('/user', userRouter);
app.use('/billing', billingRouter);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});
