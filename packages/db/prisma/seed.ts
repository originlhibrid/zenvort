import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  // Hash a default password for the test user
  const hashedPassword = await bcrypt.hash("password123", 10);

  await prisma.user.upsert({
    where: { email: "test@zenvort.com" },
    create: {
      email: "test@zenvort.com",
      password: hashedPassword,
      apiKey: "test-key-123",
      credits: 100,
      role: "admin",
    },
    update: {
      password: hashedPassword,
      role: "admin",
    },
  });

  console.log("Seeded test user:");
  console.log("  Email: test@zenvort.com");
  console.log("  Password: password123");
  console.log("  API Key: test-key-123");
  console.log("  Role: admin");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });