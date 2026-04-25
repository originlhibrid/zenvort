import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  await prisma.user.upsert({
    where: { email: "test@zenvort.dev" },
    update: {},
    create: {
      email: "test@zenvort.dev",
      apiKey: "test-key-123",
      credits: 100,
    },
  });
  console.log("Test user created");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());