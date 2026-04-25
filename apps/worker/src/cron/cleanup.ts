import cron from 'node-cron'
import { db } from '@zenvort/db'
import { deleteFile } from '@zenvort/storage'

export function startCleanupCron() {
  cron.schedule('0 * * * *', async () => {
    console.log('Running cleanup cron...')
    
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000)
    
    const expiredJobs = await db.job.findMany({
      where: {
        createdAt: { lt: cutoff },
        status: { in: ['DONE', 'FAILED'] },
        outputUrl: { not: null }
      }
    })

    for (const job of expiredJobs) {
      try {
        if (job.inputUrl) {
          const inputKey = `inputs/${job.id}/`
          try {
            await deleteFile(inputKey)
          } catch {}
        }
        if (job.outputUrl) {
          await deleteFile(`outputs/${job.id}/output.${job.outputFormat}`)
        }
        await db.job.update({
          where: { id: job.id },
          data: { outputUrl: null as any, inputUrl: null as any }
        })
        console.log(`Cleaned up job ${job.id}`)
      } catch (err) {
        console.error(`Failed to clean up job ${job.id}:`, err)
      }
    }
  })
}
