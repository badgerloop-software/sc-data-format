# Sheet sync setup

`format.json` can be regenerated from the Firmware Signal Spreadsheet via a GitHub Action or a local dry-run. This document covers one-time setup and local testing.

Parsed tabs: `PDC_SC2`, `Steering Wheel`, `MPPT`, `Powertrain`, `MCC`, `Software`, `Race Strategy`. Tabs with `SC1` in the name, plus `Title Page` and `Better Template`, are skipped. All `Battery;BMS` and `pack_power` entries are preserved from the committed `format.json`.

## Trigger the workflow

In the repo: **Actions → Sync format.json from spreadsheet → Run workflow**.

- Leave **dry_run** unchecked to sync and open a pull request.
- Check **dry_run** to parse the sheet and upload a report artifact without opening a PR.

## Required GitHub secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Yes | Full Workload Identity Provider resource name |
| `GCP_SERVICE_ACCOUNT` | Yes | Service account email |
| `GOOGLE_SHEET_FILE_ID` | Yes | Spreadsheet ID from the Google Sheet URL |
| `GEMINI_API_KEY` | No | Richer PR description; falls back to the raw diff report if unset |

`GITHUB_TOKEN` is provided automatically for PR creation.

> **Note:** Many organizations block service account JSON keys (`iam.disableServiceAccountKeyCreation`). This repo uses **Workload Identity Federation** so GitHub Actions can authenticate without a key file.

### Add GitHub secrets

In the **sc-data-format** repo: **Settings → Secrets and variables → Actions → New repository secret**.

Create one secret per row below:

| Secret name | What to paste | Where to find it |
|-------------|---------------|------------------|
| `GCP_SERVICE_ACCOUNT` | `firmware-signal-sheet-sync@firmware-signals-2-github-auto.iam.gserviceaccount.com` | **IAM & Admin → Service Accounts** → your service account email |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider` | **IAM & Admin → Workload Identity Federation** → `github-pool` → `github-provider` → copy the full provider resource name |
| `GOOGLE_SHEET_FILE_ID` | The long ID between `/d/` and `/edit` in the sheet URL | Open the Google Sheet; URL looks like `https://docs.google.com/spreadsheets/d/<FILE_ID>/edit` |

Optional fourth secret:

| Secret name | What to paste | Where to find it |
|-------------|---------------|------------------|
| `GEMINI_API_KEY` | API key string | [Google AI Studio](https://aistudio.google.com/apikey) (not Cloud Console) |

## Google Cloud setup

### Tip: Cloud Console Gemini assistant

The [Google Cloud Console](https://console.cloud.google.com/) includes a **Gemini** assistant (chat icon in the top bar). It can help you locate values for this setup without clicking through every page. Useful prompts:

- *"What is my project number for firmware-signals-2-github-auto?"*
- *"What is the full resource name for workload identity provider github-provider in pool github-pool?"*
- *"Show me the email for service account firmware-signal-sheet-sync"*
- *"Is the Google Drive API enabled in this project?"*

Use the assistant for navigation and IDs; still add the three required values as **GitHub Actions secrets** in the repo (not in GCP).

### 1. Project and Drive API

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select your project (e.g. `firmware-signals-2-github-auto`).
2. Enable the **Google Drive API** (APIs & Services → Library → Google Drive API → Enable).

### 2. Service account (no JSON key)

1. **IAM & Admin → Service Accounts → Create service account**
   - Name: `Firmware Signal Sheet Sync`
   - ID: `firmware-signal-sheet-sync`
   - Description: read-only access to the firmware signal spreadsheet for GitHub Actions
2. Skip granting project roles (not needed for a shared sheet).
3. **Do not create a JSON key** if your org blocks key creation.

### 3. Share the spreadsheet

Share the Google Sheet with the service account email as **Viewer**:

```
firmware-signal-sheet-sync@firmware-signals-2-github-auto.iam.gserviceaccount.com
```

Copy the sheet ID for the `GOOGLE_SHEET_FILE_ID` GitHub secret (see [Add GitHub secrets](#add-github-secrets)).

### 4. Workload Identity Federation pool

**IAM & Admin → Workload Identity Federation → Create pool**

| Field | Value |
|-------|--------|
| Pool name | `GitHub Pool` |
| Pool ID | `github-pool` |
| Description | GitHub Actions OIDC for firmware signal spreadsheet sync |

### 5. Add OIDC provider to the pool

| Field | Value |
|-------|--------|
| Provider type | OpenID Connect (OIDC) |
| Provider name | `GitHub Provider` |
| Provider ID | `github-provider` |
| Issuer URL | `https://token.actions.githubusercontent.com` |

**Attribute mapping**

| Google attribute | OIDC claim |
|------------------|------------|
| `google.subject` | `assertion.sub` |
| `attribute.repository` | `assertion.repository` |
| `attribute.repository_owner` | `assertion.repository_owner` |

**Attribute condition** (limit to this repo):

```
assertion.repository == 'badgerloop-software/sc-data-format'
```

Or, to allow any repo under the org:

```
assertion.repository_owner == 'badgerloop-software'
```

### 6. Allow GitHub to impersonate the service account

Find your **project number** (Home → Project settings, or `gcloud projects describe PROJECT_ID --format='value(projectNumber)'`).

Run (replace `PROJECT_NUMBER` and the service account email if different):

```bash
gcloud iam service-accounts add-iam-policy-binding \
  firmware-signal-sheet-sync@firmware-signals-2-github-auto.iam.gserviceaccount.com \
  --project=firmware-signals-2-github-auto \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/badgerloop-software/sc-data-format"
```

**Console (current UI):** open the service account → **Permissions** tab → under **Principals with access to this service account**, click **View Principals with access** → **Grant access** → add the `principalSet://…` principal above with role **Workload Identity User**.

Do **not** use **Manage service account permissions** — that assigns project roles *to* the service account and is not needed for sheet read access.

When done, **Principals with access** should show a `…github-pool/…sc-data-format` principal with role **Workload Identity User**.

### 7. Add GitHub secrets

After GCP setup, add the three required secrets in GitHub (see [Add GitHub secrets](#add-github-secrets)).

## Ready to test

1. GCP: Drive API enabled, sheet shared with service account, WIF pool + provider created, Workload Identity User binding added.
2. GitHub: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, and `GOOGLE_SHEET_FILE_ID` secrets set.
3. Repo: workflow file `.github/workflows/sync-format-from-sheet.yml` is on the default branch.
4. Run **Actions → Sync format.json from spreadsheet** with **dry_run** checked first.

## Local dry-run

Local runs use a downloaded `.xlsx` file and do not need GCP credentials:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt

python tools/sync_format.py \
  --local-xlsx /path/to/Firmware\ Signal\ Spreadsheet.xlsx \
  --dry-run
```

Review `tools/reports/sync-report.md` for added/changed signals before running the workflow without `dry_run`.

## Software and Race Strategy tabs

These tabs use the same columns as `Better Template`. They produce `FFF` placeholder entries (not decoded from CAN):

- **Software** — optional section headers `Timestamp`, `GPS`, and `Lap Counter` set the category. Firmware names must resolve to known keys (e.g. `tstamp_unix`, not only `tstamp_unix (tstamp_unix)` — the parser accepts the parenthetical form too).
- **Race Strategy** — all rows map to `Race Strategy;Model Outputs`. Use **Serial** direction for cloud-sim values the Pi forwards onto the bus.

If a tab is missing from the workbook, the sync skips it and leaves those signals unchanged.

## Fallback: service account JSON key

If your organization allows JSON keys, you can instead set `GOOGLE_SERVICE_ACCOUNT_JSON` to the full key contents and remove the `google-github-actions/auth` step from the workflow. Workload Identity Federation is preferred when keys are disabled.
