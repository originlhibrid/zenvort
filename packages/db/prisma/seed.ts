import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  await prisma.user.upsert({
    where: { email: "test@zenvort.com" },
    create: {
      email: "test@zenvort.com",
      apiKey: "test-key-123",
      credits: 100,
    },
    update: {},
  });

  console.log("Seeded test user with apiKey: test-key-123");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
