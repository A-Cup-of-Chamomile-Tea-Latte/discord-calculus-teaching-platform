# 受限 production 部署入口

## 目的

讓 `ding` 在不取得一般 root 權限、不新增 port、不修改 secrets 或 systemd units 的前提下，將已驗證
的 Calculus Discord release 部署到 production。主機 owner 只需一次性安裝入口；後續一般程式換版不
需再次輸入 owner 的 sudo 密碼。

## 權限模型

- `/usr/local/sbin/calculus-discord-deploy`：`root:root 0755`，`ding` 不可修改。
- `/etc/sudoers.d/calculus-discord-deploy`：只允許 `ding` 免密執行上述固定入口；腳本拒絕任何參數。
- candidate build 使用無 shell、無 production DB／secret 權限的 `calculus-builder`。
- 只有 verified-copy migration 與正式 migration 以 `calculus-bot` 執行；這是 production deployer
  固有的應用程式權限，不等於一般 root shell。
- 每個 release 內含精確 pin 的 dependency lock；lock 與整包 release 一起受 SHA-256 保護，且只由隔離的
  `calculus-builder` 安裝。更新套件不需要新增 root 權限，但仍須通過 staging 與部署 gate。

## 不會做的事

- 不開新 port、不建立 deployment Web API、不修改 firewall。
- 不安裝或修改 systemd unit。
- 不讀取、覆寫或輸出 `/etc/calculus-discord` runtime secrets。
- 不接受任意路徑、任意 command 或任意 sudo arguments。
- 不執行 destructive 或任意 migration target；本版只 allowlist 已獨立 rehearsal 的 additive v6→v13 chain。

## 一般部署流程

1. Host-owner bootstrap 驗證 exact archive，將 release 放入 root-owned、`ding` 不可寫的 trusted
   release 路徑；`ding` 只能從該路徑建立 inbox request。
2. 非 root preparer 只建立 mode `0600` 的四欄 request；不重新封裝或複製 release archive。
3. root-owned deployer 從 trusted release 讀取 friend bootstrap 保存的 root-owned original archive，複製到
   private staging，再驗證 SHA-256、preflight receipt、release ID、current／target schema 與 migration class。
4. `calculus-builder` 建 venv；live services 此時仍運作。
5. 以 SQLite consistent copy 執行 migration；schema、ledger、integrity 全 PASS 才允許停服務。
6. 在 root-only deploy namespace 保存 pre-deploy rollback DB，以 `calculus-bot` migration 正式 DB，
   atomic 切換 release；service account 不可替換 rollback source。
7. 固定依序啟動 course assistant、dump bot、data bridge，要求 fresh health。
8. 任一 gate 失敗，自動恢復舊 release 與舊 DB，再嘗試啟動舊服務。

## 主機 owner 的一次性安裝

Codex 先提供三個檔案的 SHA-256 manifest；主機 owner 應先以非 sudo 的 `sha256sum -c` 驗證
installer、deployer 與 sudoers template，再執行一次 bootstrap：

```bash
sudo env INSTALL_CALCULUS_DEPLOYER=INSTALL-CALCULUS-DEPLOYER \
  /var/lib/calculus-discord-deploy/releases/<release-id>/ops/scripts/install-calculus-discord-deployer.sh \
  /var/lib/calculus-discord-deploy/releases/<release-id>
```

Trusted release 必須先由 v13 friend bootstrap 建立，不可從 `/home/ding` upload tree 直接以 root 執行。
Installer 會建立 builder account、安裝 root-owned deployer、以 `visudo`
驗證最小 sudoers rule，但不會部署當次候選版。Preflight、install／repair 與 deploy 是三個分離授權；
它不要求新 port。

成功輸出至少包含：

```text
deploy_entry=INSTALLED
new_port=NO
secrets_changed=NO
systemd_units_changed=NO
deploy_executed=NO
```

之後一般換版由 `ding` 準備固定 inbox，再執行：

```bash
sudo -n /usr/local/sbin/calculus-discord-deploy
```

腳本不接受任何參數；sudoers 也以空 argument specification 限制成無參數 invocation。

## 仍須主機 owner 的情況

- 修改或移除部署器／sudoers 規則。
- 修改 systemd units、OS package、帳號、磁碟、firewall 或 port。
- 輪替 `/etc/calculus-discord` secrets。
- destructive、不可逆、跨多 schema version 的 migration。
- 自動 rollback 無法恢復的主機級事故。

本版部署器只處理 exact v6→v13 additive chain；其他 current／target 組合全部拒絕。未來 migration
必須另做獨立 rehearsal、rollback、code allowlist 與 owner 授權，不能沿用本次 `ADDITIVE` 標籤。

## 一次性撤銷

主機 owner 移除 `/etc/sudoers.d/calculus-discord-deploy` 即可立即撤銷 `ding` 的免密部署權；移除
root-owned deployer 與 builder account 可完整退役入口。撤銷不影響目前已在執行的 production release。
