-- AddFields
ALTER TABLE "Job" ADD COLUMN "converterUsed" TEXT;

-- CreateIndexes
CREATE INDEX "Job_userId_idx" ON "Job"("userId");
CREATE INDEX "Job_status_idx" ON "Job"("status");
CREATE INDEX "Job_userId_createdAt_idx" ON "Job"("userId", "createdAt" DESC);
CREATE INDEX "Job_inputUrl_outputFormat_status_idx" ON "Job"("inputUrl", "outputFormat", "status");

-- CreateIndexes
CREATE INDEX "CreditLog_userId_idx" ON "CreditLog"("userId");
CREATE INDEX "CreditLog_userId_createdAt_idx" ON "CreditLog"("userId", "createdAt" DESC);
