export type FixtureFormKind = "join" | "question" | "private-support";

export type FixtureFormValues = Record<string, string>;

export interface FixtureConfirmation {
  reference: string;
  title: string;
  publicLookup: boolean;
  persisted: false;
  summary: Array<{ label: string; value: string }>;
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const visibilityLabels: Record<string, string> = {
  CLASS: "班級可見",
  COURSE: "全課程可見",
  TEACHING_STAFF: "僅教學團隊可見",
};

const authorLabels: Record<string, string> = {
  REAL_NAME: "目前 Discord 身份",
  COURSE_ALIAS: "course alias",
  ANONYMOUS: "對一般成員匿名",
};

const analysisLabels: Record<string, string> = {
  INCLUDED: "Yes — 允許 AI 輔助教學分析",
  EXCLUDED: "No — 排除 AI 輔助教學分析",
};

function moduleForClassCode(classCode: string): string | undefined {
  const numeric = Number(classCode);
  if (numeric >= 1 && numeric <= 4) return "M1";
  if (numeric >= 5 && numeric <= 9) return "M2";
  if (numeric >= 10 && numeric <= 13) return "M3";
  if (numeric >= 14 && numeric <= 16) return "M4";
  return undefined;
}

function trimmed(values: FixtureFormValues, name: string): string {
  return (values[name] ?? "").trim();
}

function validateLength(
  errors: Record<string, string>,
  name: string,
  value: string,
  minimum: number,
  maximum: number,
  label: string,
): void {
  if (value.length < minimum) {
    errors[name] = `${label}可以再多寫一點（至少 ${minimum} 個字元）。`;
  } else if (value.length > maximum) {
    errors[name] = `${label}稍微太長了（最多 ${maximum} 個字元）。`;
  }
}

export function createAliasPreview(
  classCode: string,
  fixtureOrder = 42,
): string {
  if (!/^\d{2}$/.test(classCode) || fixtureOrder < 0 || fixtureOrder > 999) {
    return "尚未選擇班別";
  }
  return `${classCode}${String(fixtureOrder).padStart(3, "0")}`;
}

export function validateFixtureSubmission(
  kind: FixtureFormKind,
  values: FixtureFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};

  if (kind === "join") {
    const identityType = trimmed(values, "identityType");
    const discordUsername = trimmed(values, "discordUsername");
    const ntuEmail = trimmed(values, "ntuEmail").toLowerCase();
    const guestEmail = trimmed(values, "guestEmail").toLowerCase();
    const contactGmail = trimmed(values, "contactGmail").toLowerCase();
    if (
      discordUsername.length < 2 ||
      discordUsername.length > 32 ||
      /[@#:\s]/.test(discordUsername)
    ) {
      errors.discordUsername =
        "請填寫 2–32 個字元的 Discord 使用者名稱，不要加 @、# 或空格。";
    }
    if (identityType === "STUDENT") {
      if (!emailPattern.test(ntuEmail) || !ntuEmail.endsWith("@ntu.edu.tw")) {
        errors.ntuEmail = "請使用格式完整的 NTU email（結尾為 @ntu.edu.tw）。";
      }
      if (
        contactGmail &&
        (!emailPattern.test(contactGmail) ||
          !contactGmail.endsWith("@gmail.com"))
      ) {
        errors.contactGmail =
          "若要填寫聯絡 Gmail，請使用結尾為 @gmail.com 的地址。";
      }
      if (!/^(0[1-9]|1[0-6])$/.test(trimmed(values, "classCode"))) {
        errors.classCode = "請選擇 C01–C16 的正式班別。";
      }
    } else if (identityType === "GUEST") {
      if (!emailPattern.test(guestEmail)) {
        errors.guestEmail = "請填寫可聯絡的 Email。";
      }
      validateLength(
        errors,
        "guestReason",
        trimmed(values, "guestReason"),
        10,
        500,
        "來訪原因",
      );
    } else {
      errors.identityType = "請選擇學生或訪客。";
    }
    if (trimmed(values, "rulesPrivacy") !== "yes") {
      errors.rulesPrivacy = "請先確認已閱讀使用與隱私說明。";
    }
    return errors;
  }

  const title = trimmed(values, "title");
  const content = trimmed(values, "content");
  validateLength(errors, "title", title, 5, 160, "標題");
  validateLength(errors, "content", content, 20, 5000, "內容");

  if (kind === "question") {
    if (!/^(MATH|COURSEWORK|OTHER)$/.test(trimmed(values, "forum"))) {
      errors.forum = "請選擇問題要進入的 Forum。";
    }
    if (!/^(0[1-9]|1[0-6])$/.test(trimmed(values, "classCode"))) {
      errors.classCode = "請選擇 C01–C16；Module 會由班別自動推導。";
    }
    const expectedModule = moduleForClassCode(trimmed(values, "classCode"));
    if (
      !/^(M1|M2|M3|M4)$/.test(trimmed(values, "module")) ||
      trimmed(values, "module") !== expectedModule
    ) {
      errors.module = "Module 必須與 115-1 Class 對照一致。";
    }
    validateLength(
      errors,
      "mainTag",
      trimmed(values, "mainTag"),
      1,
      20,
      "主要標籤",
    );
    validateLength(
      errors,
      "problemType",
      trimmed(values, "problemType"),
      1,
      40,
      "問題類型",
    );
    if (!(trimmed(values, "visibility") in visibilityLabels)) {
      errors.visibility = "請選擇班級、全課程或僅教學團隊可見。";
    }
    if (!(trimmed(values, "authorDisplayMode") in authorLabels)) {
      errors.authorDisplayMode = "請選擇姓名、course alias 或匿名顯示。";
    }
    if (!(trimmed(values, "analysisPermission") in analysisLabels)) {
      errors.analysisPermission =
        "請明確選擇 Yes 或 No；兩者都不影響是否獲得回覆。";
    }
    if (trimmed(values, "coolAcknowledgement") !== "yes") {
      errors.coolAcknowledgement =
        "請確認正式課務仍以 NTU COOL 為準；這不會限制你提出問題。";
    }
    if (trimmed(values, "attachmentName").length > 160) {
      errors.attachmentName = "附件名稱最多 160 個字元；此原型不會上傳檔案。";
    }
    return errors;
  }

  if (trimmed(values, "privacyAcknowledgement") !== "yes") {
    errors.privacyAcknowledgement =
      "請確認了解 Portal 只會顯示 Private Support 的最小狀態，才能建立預覽。";
  }
  if (!(trimmed(values, "analysisPermission") in analysisLabels)) {
    errors.analysisPermission =
      "請明確選擇 Yes 或 No；Portal 不會顯示 Private Support 的內容。";
  }
  return errors;
}

export function createFixtureConfirmation(
  kind: FixtureFormKind,
  values: FixtureFormValues,
): FixtureConfirmation {
  if (kind === "join") {
    const isGuest = trimmed(values, "identityType") === "GUEST";
    return {
      reference: "PREVIEW-JOIN-001",
      title: isGuest ? "訪客審核預覽已建立" : "加入與設定預覽已建立",
      publicLookup: false,
      persisted: false,
      summary: [
        { label: "申請身份", value: isGuest ? "訪客" : "學生" },
        {
          label: "Discord 使用者名稱",
          value: trimmed(values, "discordUsername"),
        },
        ...(isGuest
          ? [
              { label: "聯絡 Email", value: trimmed(values, "guestEmail") },
              { label: "審核方式", value: "由管理員人工確認" },
            ]
          : [
              { label: "NTU email", value: trimmed(values, "ntuEmail") },
              {
                label: "聯絡 Gmail",
                value: trimmed(values, "contactGmail") || "未提供",
              },
              { label: "班別", value: `C${trimmed(values, "classCode")}` },
            ]),
      ],
    };
  }

  if (kind === "question") {
    return {
      reference: "C01-N4Y7D2-0723-1030",
      title: "一般問題預覽已建立（未送出）",
      publicLookup: false,
      persisted: false,
      summary: [
        { label: "標題", value: trimmed(values, "title") },
        { label: "Forum", value: trimmed(values, "forum") },
        { label: "Class", value: `C${trimmed(values, "classCode")}` },
        {
          label: "Discord 標題預覽",
          value: `[${trimmed(values, "module")} | C${trimmed(values, "classCode")}][${trimmed(values, "mainTag")}] ${trimmed(values, "title")}`,
        },
        {
          label: "可見範圍",
          value: visibilityLabels[trimmed(values, "visibility")],
        },
        {
          label: "作者顯示",
          value: authorLabels[trimmed(values, "authorDisplayMode")],
        },
        {
          label: "提問者的 AI 分析選擇",
          value: analysisLabels[trimmed(values, "analysisPermission")],
        },
        {
          label: "附件資訊",
          value: trimmed(values, "attachmentName") || "未提供",
        },
      ],
    };
  }

  return {
    reference: "C99-F6Q2S8-0723-1031-P",
    title: "Private Support 預覽已建立（未送出）",
    publicLookup: false,
    persisted: false,
    summary: [
      { label: "主旨", value: trimmed(values, "title") },
      { label: "可見範圍", value: "僅授權教學團隊" },
      {
        label: "Private 案號",
        value: "C99-F6Q2S8-0723-1031-P（只查最小狀態）",
      },
      {
        label: "AI 輔助教學分析",
        value: analysisLabels[trimmed(values, "analysisPermission")],
      },
    ],
  };
}
