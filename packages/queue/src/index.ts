import { Queue } from "bullmq";
import redisConnection from "./connection.js";

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
});