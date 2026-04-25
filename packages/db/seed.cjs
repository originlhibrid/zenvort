const { PrismaClient } = require('/app/node_modules/.pnpm/@prisma+client@5.22.0_prisma@5.22.0/node_modules/@prisma/client');

const db = new PrismaClient();

async function main() {
  const user = await db.user.upsert({
    where: { email: 'test@zenvort.com' },
    create: { email: 'test@zenvort.com', apiKey: 'test-key-123', credits: 100 },
    update: {}
  });
  console.log('Seeded test user with apiKey: test-key-123', user.id);
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => db.$disconnect());
