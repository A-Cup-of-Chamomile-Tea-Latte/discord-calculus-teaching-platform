# 系統脈絡與信任邊界

下圖是第一版原型的責任與資料流，不是已核准的正式部署圖。實線表示預期互動；標示 `mock first` 的外部介接在本地與 CI 使用 fixtures/adapters。

```mermaid
flowchart LR
  student["學生"]
  staff["助教／教師"]
  manager["授權管理者"]
  cool["NTU COOL<br/>正式課務依據"]

  subgraph public["公開瀏覽器邊界"]
    portal["Astro static portal"]
  end

  subgraph controlled["受控服務／機器人邊界（mock first）"]
    api["Case / onboarding adapters"]
    commandApi["Authenticated bot command boundary<br/>unresolved / mock only"]
    courseBot["course_assistant bot"]
    archiveBot["dump_bot bot"]
    gas["Apps Script admin API"]
  end

  subgraph external["外部平台（尚未連正式服務）"]
    discord["Discord"]
    sheets["Google Sheets"]
    email["Email delivery"]
  end

  subgraph local["管理者本機邊界"]
    exportTool["Explicit export pipeline"]
    anonymizer["Consent + anonymizer"]
    importer["Batch importer"]
  end

  contracts["Versioned contracts + fictional fixtures"]

  student --> cool
  staff --> cool
  student --> portal
  staff --> portal
  student --> discord
  staff --> discord
  portal -->|"單筆一般案件／表單"| api
  api -->|"mock 或授權後"| gas
  api -->|"mock email"| email
  api -.->|"future authenticated command"| commandApi
  commandApi -.->|"writer service only"| courseBot
  courseBot <-->|"互動與寫入"| discord
  archiveBot <-->|"選定 thread 讀取"| discord
  manager --> exportTool
  archiveBot -->|"結構化資料"| exportTool
  exportTool --> anonymizer
  anonymizer --> importer
  importer -->|"授權後批次"| gas
  gas <--> sheets
  contracts -.-> portal
  contracts -.-> api
  contracts -.-> courseBot
  contracts -.-> archiveBot
  contracts -.-> exportTool
  contracts -.-> gas
```

## 安全讀法

- 瀏覽器只取得公開設定與最小化 API response；圖中沒有、實作也不得加入瀏覽器到 bot token 的路徑。
- 每個 bot token 只由該 bot 的 runtime environment 注入；`course_assistant` 與 `dump_bot` 不共用 token。
- `course_assistant`是interaction/write唯一owner；`dump_bot`只有explicit selected-thread read，沒有send/role/nickname能力。
- `commandApi`是Task 32前的未決/mock boundary，不表示Portal或GAS已能直連Discord。Browser→Discord REST永遠禁止。
- Private Support 經獨立 policy 投影，公開 Portal query 不得碰觸其內容。
- 原始匯出只存在授權管理者的 Git-ignored 本機資料區；匿名化與同意判定先於分析／批次匯入。
- NTU COOL 與本系統沒有自動同步；它仍是正式課務來源。
