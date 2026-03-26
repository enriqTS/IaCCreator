import { describe, it, expect, vi, beforeEach } from "vitest";

describe("Next.js rewrite configuration", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("should expose an async rewrites function", async () => {
    const { default: config } = await import("../next.config.ts");
    expect(config.rewrites).toBeDefined();
    expect(typeof config.rewrites).toBe("function");
  });

  it("should define rewrite rules for /api and /generate paths", async () => {
    const { default: config } = await import("../next.config.ts");
    const rewrites = (await config.rewrites!()) as Array<{
      source: string;
      destination: string;
    }>;

    expect(rewrites).toHaveLength(2);

    const sources = rewrites.map((r) => r.source);
    expect(sources).toContain("/api/:path*");
    expect(sources).toContain("/generate/:path*");
  });

  it("should use default backend URL http://localhost:8000 when env var is not set", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");

    const { default: config } = await import("../next.config.ts");
    const rewrites = (await config.rewrites!()) as Array<{
      source: string;
      destination: string;
    }>;

    const apiRule = rewrites.find((r) => r.source === "/api/:path*");
    const generateRule = rewrites.find((r) => r.source === "/generate/:path*");

    expect(apiRule!.destination).toBe("http://localhost:8000/api/:path*");
    expect(generateRule!.destination).toBe(
      "http://localhost:8000/generate/:path*"
    );
  });

  it("should use NEXT_PUBLIC_API_URL when set", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://my-backend:9000");

    const { default: config } = await import("../next.config.ts");
    const rewrites = (await config.rewrites!()) as Array<{
      source: string;
      destination: string;
    }>;

    const apiRule = rewrites.find((r) => r.source === "/api/:path*");
    const generateRule = rewrites.find((r) => r.source === "/generate/:path*");

    expect(apiRule!.destination).toBe("http://my-backend:9000/api/:path*");
    expect(generateRule!.destination).toBe(
      "http://my-backend:9000/generate/:path*"
    );
  });
});
