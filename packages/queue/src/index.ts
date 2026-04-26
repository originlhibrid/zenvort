import { Queue } from "bullmq";
import { redisConnection } from "./connection.js";

export { redisConnection };

export type ConversionJobData = {
  jobId: string;
  inputUrl: string;
  inputFormat: string;
  outputFormat: string;
  userId?: string;
};

export const conversionsQueue = new Queue<ConversionJobData>("conversions", {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: "exponential",
      delay: 5000,
    },
    removeOnComplete: 100,
    removeOnFail: 200,
  } as any, // timeout handled by worker lockDuration
});