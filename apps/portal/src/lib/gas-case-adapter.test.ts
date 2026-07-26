import { describe, expect, it } from "vitest";

import { fixtureCaseService } from "../../../gas/src/cases/fixture-service";
import type { CaseLookupResponse } from "../../../gas/src/cases/contracts";
import { FixtureCaseLookupAdapter } from "./fixture-case-adapter";
import {
  GasCaseLookupAdapter,
  type GasCaseApiTransport,
  type GasCaseLookupResponse,
} from "./gas-case-adapter";

class LocalGasFixtureTransport implements GasCaseApiTransport {
  async lookup(caseNumber: string): Promise<GasCaseLookupResponse> {
    return fixtureCaseService.lookup(caseNumber) as GasCaseLookupResponse;
  }

  async listPublicCases(): Promise<GasCaseLookupResponse[]> {
    return fixtureCaseService.listPublic() as GasCaseLookupResponse[];
  }
}

describe("Portal fixture / GAS fixture compatibility", () => {
  const portalFixture = new FixtureCaseLookupAdapter();
  const gasFixture = new GasCaseLookupAdapter(new LocalGasFixtureTransport());

  for (const caseNumber of [
    "C01-7K4M2Q-0702-1000",
    "C02-R8N6WX-0702-1100",
    "C01-P3T7V9-0702-1200",
    "C01-H5J8Q4-0702-1300",
    "C02-M6X2C7-0702-1400",
  ]) {
    it(`returns compatible public fields for ${caseNumber}`, async () => {
      const [portalResult, gasResult] = await Promise.all([
        portalFixture.lookup(caseNumber),
        gasFixture.lookup(caseNumber),
      ]);
      expect(gasResult.outcome).toBe("FOUND");
      expect(portalResult.outcome).toBe("FOUND");
      if (gasResult.outcome === "FOUND" && portalResult.outcome === "FOUND") {
        expect(gasResult.case).toMatchObject({
          caseNumber: portalResult.case.caseNumber,
          status: portalResult.case.status,
          visibility: portalResult.case.visibility,
          updatedAt: portalResult.case.updatedAt,
        });
      }
    });
  }

  it("excludes Private Support from public results", async () => {
    expect((await gasFixture.lookup("C99-B4W9K6-0702-1500-P")).outcome).toBe(
      "NOT_FOUND",
    );
    const listed = await gasFixture.listPublicCases();
    expect(listed.map((item) => item.caseNumber)).toEqual([
      "C01-7K4M2Q-0702-1000",
      "C02-R8N6WX-0702-1100",
      "C01-P3T7V9-0702-1200",
      "C01-H5J8Q4-0702-1300",
      "C02-M6X2C7-0702-1400",
    ]);
    expect(JSON.stringify(listed)).not.toContain("PRIVATE_SUPPORT");
  });

  it("does not project backend IDs, hashes, tokens, or secrets", async () => {
    const response: CaseLookupResponse = fixtureCaseService.lookup(
      "C01-7K4M2Q-0702-1000",
    );
    expect(JSON.stringify(response)).not.toMatch(
      /caseId|userId|discord|verifierHash|token|secret/i,
    );
  });

  it("rejects an unexpected backend field instead of passing it to the UI", async () => {
    const unsafeTransport: GasCaseApiTransport = {
      async lookup() {
        return {
          ...fixtureCaseService.lookup("C01-7K4M2Q-0702-1000"),
          internalToken: "must-not-pass",
        } as GasCaseLookupResponse;
      },
      async listPublicCases() {
        return [];
      },
    };
    await expect(
      new GasCaseLookupAdapter(unsafeTransport).lookup("C01-7K4M2Q-0702-1000"),
    ).rejects.toThrow("INVALID_GAS_CASE_RESPONSE");
  });
});
