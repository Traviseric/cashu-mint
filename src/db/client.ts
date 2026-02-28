import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient | undefined };

/** Singleton Prisma client — reuses instance across hot-reloads in dev */
export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') {
	globalForPrisma.prisma = prisma;
}
