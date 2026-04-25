const { PrismaClient } = require('@prisma/client');

const db = new PrismaClient();

async function main() {
  // Note: bcrypt can't be used in seed directly, password will be hash manually
  // For now, create user without password - they'll need to use forgot password flow
  // Or use a pre-hashed password
  
  await db.user.upsert({
    where: { email: 'test@zenvort.com' },
    create: { 
      email: 'test@zenvort.com', 
      apiKey: 'test-key-123', 
      credits: 100,
      role: 'admin'
    },
    update: { role: 'admin' }
  });
  
  console.log('Seeded test user:');
  console.log('  Email: test@zenvort.com');
  console.log('  API Key: test-key-123');
  console.log('  Role: admin');
  console.log('  (Password not set - use signup or update manually)');
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => db.$disconnect());