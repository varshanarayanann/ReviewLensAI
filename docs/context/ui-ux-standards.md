# ReviewLens AI - UI/UX Standards Context Document

**Story:** S1-002 - Create UI/UX Standards Context Document
**Canonical rules:** S1-BR-003, S1-BR-015, S1-BR-025
**Audience:** Every developer on the team and every AI coding tool (Cursor, Claude Code, Copilot, Codex, etc.) that generates or modifies ReviewLens UI code.

---

## 0. How To Use This Document

1. Read this document before building or changing any screen, form, or component.
2. When prompting an AI coding tool to build UI, include this file in the tool's context and instruct it to follow it.
3. If something you need is not covered here, choose the option most consistent with what already exists, then update this document in the same pull request.
4. Precedence when documents conflict:
   1. Active sprint story file (currently Sprint 1).
   2. Instructor UX reference (`ReviewLens-UX-Implementation-Reference.md` and the UX reference image).
   3. Team Sprint 1 Architecture Baseline.
   4. This document.
   5. Individual developer preference (lowest).

The goal: **ReviewLens must feel like one product, not 23 stories stitched together.** If two developers build two different pages from this document, a user should not be able to tell they were built by different people.

### 0.1 Stack Context (from the Sprint 1 Architecture Baseline)

| Concern | Team decision | UI implication |
| --- | --- | --- |
| Frontend | React + TypeScript | All components are typed React function components |
| Backend | Python FastAPI (`/api/...`) | The UI talks only to our FastAPI backend, never to third-party review services directly |
| Authentication | Supabase Auth | We build our own Log in / Register / Reset password screens using the Supabase client SDK; Supabase supplies the identity, sessions, and password reset |
| Review platform | **Google Maps** | Platform is fixed; shown as a read-only `Google Maps` badge everywhere |
| Ingestion | URL-initiated ingestion (primary) + CSV upload (secondary recovery path) | See Section 6.3 and Section 11 |
| Icons | `lucide-react` | Only icon library allowed |
| Deployment | Netlify (frontend), Render (backend) | No environment-specific URLs hard-coded in components |

### 0.2 Frontend File Locations

| What | Location |
| --- | --- |
| Design tokens (CSS variables) | `frontend/src/styles/tokens.css` |
| Shared UI components (Section 8) | `frontend/src/components/ui/` |
| App shell and layout components | `frontend/src/components/layout/` |
| Pages (one per route) | `frontend/src/pages/` |
| API client and error mapping | `frontend/src/lib/api/` |
| User-facing message strings | `frontend/src/lib/messages.ts` |

If the Engineering Coding Standards document (S1-001) defines a different folder layout, S1-001 wins and this table is updated to match.

---

## 1. Product Experience Principles

These principles override any individual layout decision.

1. **The Analysis Workspace is the center of gravity.** Everything else (log in, dashboard, account) exists to get the user into a workspace.
2. **The active target is never ambiguous.** On any screen that operates on a target, the target name, review platform, and source must be visible without scrolling.
3. **State is always explicit.** The user never has to guess whether something is loading, succeeded, failed, or has not happened yet.
4. **ReviewLens is an analysis tool, not a chatbot.** Visual language should look like a professional analytics product: calm, structured, data-first.
5. **Errors speak the user's language.** Every error says what happened and what to do next. No stack traces, database messages, HTTP client errors, FastAPI validation dumps, or Supabase error text on screen (S1-BR-025).
6. **No fake data on screen.** Never render placeholder reviews, sample ratings, or "demo" content as if it were real ingested data.

---

## 2. Application Navigation

### 2.1 Navigation pattern (fixed)

ReviewLens uses a **persistent left sidebar + top header** app shell for all authenticated pages. Do not introduce top-tab navigation, a second sidebar, or page-specific navigation paradigms. Tabs are allowed only *inside* the Analysis Workspace (Section 3.3).

```
+--------------------------------------------------------------+
| Header: ReviewLens logo            [breadcrumbs]  [Account v]|
+-----------+--------------------------------------------------+
| Sidebar   | Main content                                     |
|           |                                                  |
| Dashboard |  Page header (title + primary action)            |
| + New     |                                                  |
|   target  |  Page body                                       |
|           |                                                  |
| ACTIVE    |                                                  |
| TARGET    |                                                  |
| <name>    |                                                  |
| [Google   |                                                  |
|  Maps]    |                                                  |
+-----------+--------------------------------------------------+
```

Sidebar contents (top to bottom):

| Item | Behavior |
| --- | --- |
| **Dashboard** | Links to the dashboard / target list (`/dashboard`). Highlighted when on it. |
| **New target** button | Opens the create-target page (`/targets/new`). Always visible. |
| **Active target** section | Shows the currently open target's name and `Google Maps` badge. Hidden when no target is open. Clicking it returns to that target's workspace. |

Header right side: **Account menu** (`AccountMenu` component) showing the signed-in user's email, with a `Log out` item.

### 2.2 Route map

Use these routes. Do not invent alternate URLs for the same screen.

| Route | Screen | Auth required |
| --- | --- | --- |
| `/` | Redirects to `/dashboard` if logged in, otherwise to `/login` | No |
| `/login` | Log in | No (redirects to `/dashboard` if already logged in) |
| `/register` | Register | No (redirects to `/dashboard` if already logged in) |
| `/forgot-password` | Request password reset email | No |
| `/reset-password` | Set new password (Supabase recovery link lands here) | Recovery session |
| `/dashboard` | Dashboard: my analysis targets | Yes |
| `/targets/new` | Create analysis target | Yes |
| `/targets/:targetId` | Analysis Workspace for one target | Yes |
| any unknown route | Not Found page | No |

Frontend routes are separate from backend API routes (`/api/targets`, `/api/targets/{id}/ingestions`, etc.). Pages never build API URLs by hand; they call the typed client in `frontend/src/lib/api/`.

### 2.3 Navigation rules

- **Protected routes (S1-BR-003):** An unauthenticated visit to any protected route redirects to `/login` and returns the user to the originally requested route after log in. While the Supabase session is being restored on page load, show the app-shell skeleton, never protected content followed by a redirect.
- **Route guards are UX, not security.** The FastAPI backend independently rejects unauthenticated and cross-user requests. The UI must still handle those backend responses correctly (see Section 5.4).
- **Breadcrumbs** appear in the header on nested pages: `Dashboard / <Target name>` and `Dashboard / New target`.
- **Log out** calls Supabase `signOut()`, clears all client-side cached target/review data, and navigates to `/login`. The next user on the same browser must never see the previous user's data (S1-BR-006).
- After **creating a target**, navigate directly to that target's workspace (`/targets/:targetId`).
- The browser back button must work normally. Do not use modal-only flows for anything that should be a page.

---

## 3. Page Layout

### 3.1 App shell dimensions

| Element | Desktop (>= 1024px) | Tablet (768-1023px) | Mobile (< 768px) |
| --- | --- | --- | --- |
| Header height | 56px | 56px | 56px |
| Sidebar | 240px fixed, always visible | Collapsible, overlays content | Hidden behind a menu button (drawer) |
| Main content max width | 1200px, centered | Full width | Full width |
| Main content padding | 32px | 24px | 16px |

ReviewLens is **desktop-first**. Design and test desktop first, then confirm tablet and mobile remain usable (no horizontal scrolling, no clipped actions, no overlapping text).

### 3.2 Standard page structure

Every authenticated page follows this order:

1. **Page header**: `h1` title on the left; at most one primary action button on the right. Optional one-line description under the title in secondary text color.
2. **Page-level alert area** (only when needed): errors or notices that apply to the whole page.
3. **Page body**: cards/panels laid out on the spacing scale.

Auth pages (`/login`, `/register`, `/forgot-password`, `/reset-password`) do **not** use the app shell. They use the `AuthLayout`: centered 400px card on `--color-bg`, ReviewLens logo above the card, one form per page.

### 3.3 Analysis Workspace layout (`/targets/:targetId`)

The workspace is the most important screen. It always contains, in this order:

1. **Target context header** (`TargetContextHeader` component, sticky at top of the content area):
   - Target name (`h1`).
   - `Google Maps` platform badge.
   - Source URL shown as a truncated, clickable external link (opens in new tab, `rel="noopener noreferrer"`), with the full URL in a tooltip/title.
   - Ingestion status badge (see Section 6.3).
   - Created date in secondary text.
   - `Delete target` as a ghost button in an overflow menu (never a primary button).
2. **Workspace tabs** (`WorkspaceTabs` component). The tab bar sits directly under the context header so the active target stays visible above every tab.

| Tab | Sprint | Contents |
| --- | --- | --- |
| **Reviews** | Sprint 1 | Ingestion panel + persisted review list |
| **Summary** | Sprint 2 | Review statistics (architecture baseline "Review Summary") |
| **Ask** | Sprint 2 | Review-grounded Q&A (architecture baseline "AI Chat") |

Sprint 1 rule: render **only the Reviews tab**. When only one tab exists, the tab bar may be hidden. Do not show disabled or "coming soon" Summary/Ask tabs, chart placeholders, or a chat box in Sprint 1.

**Reviews tab layout (Sprint 1):**

1. **Ingestion panel**: latest ingestion state, the primary `Ingest reviews` action (from the source URL), the secondary `Upload a CSV instead` action, and the result message of the latest attempt.
2. **Reviews panel**: persisted reviews for this target (`Reviews (N)` header + list), or an empty state if none.

### 3.4 Dashboard layout (`/dashboard`)

- Page header: title `Dashboard`, description `Your analysis targets`, primary action `New target`.
- Targets render as a responsive grid of `TargetCard`s (3 columns desktop, 2 tablet, 1 mobile).
- Each card shows: target name, `Google Maps` badge, source reference (truncated, e.g. `google.com/maps/place/Joe's+Pizza...`), latest ingestion status badge, review count (from the API, when available), and created date. The whole card is clickable and opens the workspace.
- Sort: most recently created first.

---

## 4. Visual Language

### 4.1 Color tokens

Define these once as CSS variables in `frontend/src/styles/tokens.css`. **Never hard-code hex values in components.**

| Token | Value | Use |
| --- | --- | --- |
| `--color-primary` | `#4F46E5` (indigo 600) | Primary buttons, active nav item, links, focus ring |
| `--color-primary-hover` | `#4338CA` | Primary hover |
| `--color-bg` | `#F8FAFC` | App background |
| `--color-surface` | `#FFFFFF` | Cards, panels, inputs |
| `--color-border` | `#E2E8F0` | Card and input borders, dividers |
| `--color-text` | `#0F172A` | Primary text |
| `--color-text-muted` | `#64748B` | Secondary text, helper text, timestamps |
| `--color-success` | `#16A34A` (bg `#DCFCE7`) | Successful ingestion |
| `--color-warning` | `#D97706` (bg `#FEF3C7`) | Partial success, skipped rows, cautions |
| `--color-danger` | `#DC2626` (bg `#FEE2E2`) | Errors, failed ingestion, destructive actions |
| `--color-info` | `#2563EB` (bg `#DBEAFE`) | Processing, neutral information |
| `--color-neutral` | `#475569` (bg `#F1F5F9`) | "Not ingested" / inactive states |
| `--color-rating` | `#F59E0B` | Star rating fill only |

Rules:
- Status colors are reserved for status. Do not use green/red/amber decoratively.
- Never communicate status with color alone; always pair with a text label and/or icon.
- All text must meet WCAG AA contrast (4.5:1 normal text, 3:1 large text and UI controls).

### 4.2 Typography

- **Font:** `Inter`, falling back to `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- **Monospace** (IDs, URLs in technical contexts only): `ui-monospace, "JetBrains Mono", Consolas, monospace`.

| Style | Size / line height | Weight | Use |
| --- | --- | --- | --- |
| H1 | 24px / 32px | 600 | Page title, target name in workspace |
| H2 | 20px / 28px | 600 | Panel/section titles |
| H3 | 16px / 24px | 600 | Card titles, sub-sections |
| Body | 14px / 20px | 400 | Default text |
| Body strong | 14px / 20px | 500 | Labels, emphasized values |
| Small | 12px / 16px | 400 | Helper text, timestamps, badges |

Rules:
- Exactly one `h1` per page. Do not skip heading levels.
- **Sentence case** for all titles, labels, and buttons (`Create target`, not `Create Target`).
- Do not use font sizes outside this scale.

### 4.3 Spacing, radius, elevation

- **Spacing scale (4px base):** `4, 8, 12, 16, 24, 32, 48, 64` px. Use only these values for margin, padding, and gaps.
  - Inside a form field group (label - input - helper): 4-8px.
  - Between form fields: 16px.
  - Between cards / panels: 24px.
  - Between major page sections: 32px.
  - Card internal padding: 24px desktop, 16px mobile.
- **Border radius:** 6px for inputs/buttons, 12px for cards/panels/dialogs, full (pill) for badges.
- **Elevation:** cards use a 1px `--color-border` border and at most a subtle shadow (`0 1px 2px rgba(15, 23, 42, 0.06)`). Dialogs and dropdowns may use a stronger shadow. No heavy drop shadows or gradients.

### 4.4 Icons

- Use **`lucide-react` only**. Do not add another icon library.
- Icons are 16px inline with text, 20px in buttons/headers.
- Decorative icons get `aria-hidden="true"`; icon-only buttons require an `aria-label`.

---

## 5. Forms, Validation, and Error Presentation

### 5.1 Form conventions

- **Labels** sit above inputs, always visible. Never use placeholder text as the only label.
- **Required fields** are marked with a `*` after the label and the form shows `* Required` once near the top. Optional fields say `(optional)` instead.
- **Placeholders** show an example format only (e.g. `https://www.google.com/maps/place/...`), never instructions.
- **Helper text** sits under the input in `Small` / `--color-text-muted` and explains format or purpose.
- **Field width**: inputs fill the form column; form column max width is 560px (400px on auth pages).
- **Actions** sit at the bottom of the form, right-aligned on desktop, full-width stacked on mobile: primary action on the right, `Cancel` (secondary) to its left. Auth forms use a single full-width primary button.
- **Enter** submits the form. The first invalid field receives focus after a failed submit.
- **Preserve input** after a failed submit (except password fields). Never clear the form because the server rejected it.
- **Platform field:** ReviewLens supports exactly one review platform (S1-BR-012), so the create-target form shows a **read-only `Google Maps` badge** labelled `Review platform`, not a dropdown.

### 5.2 Create-target form (`/targets/new`)

Submits to `POST /api/targets`. The request body never includes a user ID or owner ID; the backend derives the owner from the Supabase token (S1-BR-010).

| Field | Control | Rules (frontend mirrors backend; backend is authoritative) |
| --- | --- | --- |
| Target name * | Text input | Required, trimmed, 1-120 characters |
| Review platform | Read-only `Google Maps` badge | Fixed by team configuration |
| Google Maps URL * | URL input (`type="url"`) | Required; valid `https://` URL; host must be a Google Maps URL: `www.google.com/maps/...`, `google.com/maps/...`, `maps.google.com/...`, `maps.app.goo.gl/...`, or `goo.gl/maps/...` |

- Helper text under the URL field: `Open the business in Google Maps, then copy the link from your browser's address bar or the Share button.`
- Primary action: `Create target`. Secondary: `Cancel` (returns to `/dashboard`).
- On success: toast `Target created`, then navigate to `/targets/:targetId`.

### 5.3 Validation behavior (S1-BR-015)

- **When to validate on the client:** on blur for each field, and on submit for all fields. Do not show errors while the user is still typing in a field they have not yet left.
- **The backend is authoritative.** Client validation is a convenience. The UI must also display validation errors returned by FastAPI, mapped to the matching field. The API client in `frontend/src/lib/api/` is the only place that translates backend error responses (including FastAPI `422` `detail[].loc` field paths) into `{ field, message }` pairs for forms.
- **Inline field error:** shown directly under the input in `--color-danger`, with an error icon, linked to the input with `aria-describedby`; the input gets `aria-invalid="true"` and a red border.
- **Form error summary:** when submit fails, show an `Alert` (danger) at the top of the form: `Please fix the highlighted fields.` For a non-field server error, put the mapped message here instead.
- **No partial state:** a rejected form must not create a target. Do not navigate away on a failed submit.

Standard validation messages (reuse this exact wording; store in `frontend/src/lib/messages.ts`):

| Condition | Message |
| --- | --- |
| Missing target name | `Enter a target name.` |
| Target name too long | `Target name must be 120 characters or fewer.` |
| Missing source URL | `Enter the Google Maps URL for this business.` |
| Not a URL | `Enter a valid URL that starts with https://` |
| URL is not a Google Maps URL | `This isn't a Google Maps link. Paste the link to the business's Google Maps page.` |

### 5.4 Error categories and how each is presented

The UI must distinguish these categories (technical spec Section 5.1). Never collapse them into one generic "Something went wrong."

| Category | Backend signal | Presentation | Message |
| --- | --- | --- | --- |
| Validation failure | `400` / `422` | Inline field errors + form summary | See Section 5.3 |
| Authentication / session expired | `401` | Toast, then redirect to `/login` and back after log in | `Your session has ended. Please log in again.` |
| Authorization / not found | `403` or `404` on a target | `NotFoundState` inside the app shell | `We couldn't find that analysis target. It may have been deleted, or you may not have access to it.` |
| Ingestion: source URL unusable / no reviews found | Ingestion run `failed` | Danger `Alert` in Ingestion panel + `Failed` badge | `We couldn't find reviews at this Google Maps link. Check that the link opens a business page with reviews.` |
| Ingestion: review provider timeout | Ingestion run `failed` | Danger `Alert` in Ingestion panel | `Google Maps reviews took too long to load. Try again in a few minutes.` |
| Ingestion: review provider unavailable | Ingestion run `failed` | Danger `Alert` in Ingestion panel | `We can't reach the review source right now. Try again later, or upload a CSV instead.` |
| Ingestion: quota exhausted | Ingestion run `failed` | Warning `Alert` in Ingestion panel | `ReviewLens has reached its review-collection limit for now. Try again later, or upload a CSV instead.` |
| CSV: wrong file type / too large / empty | `400` / `422` | Inline error under the file field | See Section 5.6 |
| CSV: missing required columns | `422` | Danger `Alert` in Ingestion panel | `This CSV is missing required columns. It needs a "rating" column and a "review_text" column.` (column names pending S1-020 / S1-021) |
| CSV: no valid rows | Ingestion run `failed` | Danger `Alert` in Ingestion panel | `None of the rows in this file had both a rating and review text, so nothing was imported.` |
| Network failure (offline) | Request never completes | Toast; keep current data on screen | `You appear to be offline. Check your connection and try again.` |
| Unexpected application failure | `500` | Danger `Alert` at page or panel level | `Something went wrong on our side. Try again, and contact the team if it keeps happening.` |

Rules:
- **Authorization denial and not-found look identical** to the user. Never confirm that another user's target exists.
- **Never display** raw exception messages, stack traces, SQL/Postgres errors, FastAPI `detail` dumps, Supabase error strings, HTTP client errors, tokens, or secrets. The backend logs technical details; the UI shows the mapped message.
- **Every error message has two parts:** what happened, then what the user can do next.
- A failed ingestion **must not hide or clear** previously persisted reviews; the Reviews panel keeps showing existing data.

### 5.5 Auth forms (Supabase Auth)

| Page | Fields | Primary action | Secondary links |
| --- | --- | --- | --- |
| `/login` | Email *, Password * | `Log in` | `Forgot password?`, `Don't have an account? Register` |
| `/register` | Email *, Password *, Confirm password * | `Create account` | `Already have an account? Log in` |
| `/forgot-password` | Email * | `Send reset link` | `Back to log in` |
| `/reset-password` | New password *, Confirm password * | `Update password` | none |

Password fields have a show/hide toggle (icon button with `aria-label="Show password"` / `"Hide password"`). Password requirements are shown as helper text before the user submits.

Supabase errors are mapped; **never render the Supabase message string**:

| Situation | Message |
| --- | --- |
| Wrong email or password | `Email or password is incorrect.` |
| Email already registered | `An account with this email already exists. Log in instead.` |
| Email not confirmed | `Confirm your email address using the link we sent you, then log in.` |
| Weak password | `Password must be at least 8 characters.` (match the team's Supabase password policy) |
| Passwords don't match | `Passwords don't match.` |
| Too many attempts | `Too many attempts. Wait a few minutes and try again.` |
| Reset email sent | Success `Alert`: `If an account exists for that email, we've sent a password reset link.` (same message whether or not the email exists) |

### 5.6 CSV upload field (secondary ingestion path)

- Uses the `FileUploadField` component: label `Reviews CSV file`, a drop zone plus a `Choose file` button, `accept=".csv"`.
- Helper text lists the expected format: `CSV with columns: rating (1-5), review_text. Optional: reviewer_name, review_date, review_url.` The exact column names must match the backend parser and the team's documented CSV format.

> **Pending (S1-020 / S1-021):** CSV column names and max file size / row limit are finalized when the backend parser is built. The authoritative format will live in `docs/csv-import-format.md`; update the helper text above and the messages below to match it.
- After choosing a file, show the file name and size with a `Remove` ghost button before upload.
- Client-side checks (backend re-validates):

| Condition | Message |
| --- | --- |
| Not a `.csv` file | `Choose a .csv file.` |
| File too large | `This file is larger than <max size>. Split it into smaller files.` (max size from configuration, defined in S1-008 / S1-020) |
| Empty file | `This file is empty.` |

- Primary action inside the upload area: `Upload reviews`, which becomes `Uploading...` while in progress.

### 5.7 Where messages appear

| Mechanism | Use for | Do not use for |
| --- | --- | --- |
| Inline field error | One field's validation | Anything not tied to a field |
| `Alert` (inline banner) | Errors/results scoped to a page, form, or panel; ingestion results | Short confirmations |
| Toast | Brief confirmations (`Target created`, `Target deleted`) and transient notices (offline, session ended). Auto-dismiss after 5s; error toasts do not auto-dismiss. | The only record of a failure the user must act on |
| Full-page state | Not found / no access, unrecoverable page load failure | Field validation |

---

## 6. Loading, Processing, and Status States

### 6.1 Loading rules

- **Initial page/data load:** show `Skeleton` placeholders shaped like the content (cards, header, list rows). No blank pages and no full-screen spinners.
- **Session restore on app load:** show the app-shell skeleton until Supabase reports whether a session exists.
- **Button actions:** the clicked button shows an inline spinner, changes its label to the in-progress verb, and is disabled until the request settles: `Create target` becomes `Creating...`; `Ingest reviews` becomes `Ingesting...`; `Log in` becomes `Logging in...`.
- **Prevent double submission** of any mutating action.
- **Do not block the whole page** for a scoped action; only the affected panel/button shows progress.
- Loading indicators appear only after 300ms to avoid flicker on fast responses.
- Announce async results to screen readers with an `aria-live="polite"` region.

### 6.2 Empty states

Every list/panel that can be empty uses the `EmptyState` component: icon, one-line title, one-line explanation, and the next action.

| Where | Title | Description | Action |
| --- | --- | --- | --- |
| Dashboard, no targets | `No analysis targets yet` | `Add a Google Maps business to start analyzing its reviews.` | `New target` |
| Workspace, never ingested | `No reviews ingested yet` | `Collect reviews from this target's Google Maps page.` | `Ingest reviews` |
| Workspace, last ingestion failed and none persisted | `No reviews available` | `The last ingestion didn't collect any reviews.` | `Try again` |

### 6.3 Ingestion status and Ingestion panel (S1-BR-023)

Ingestion state is shown with the `StatusBadge` component, using exactly these labels and colors everywhere (target cards, workspace header, ingestion panel). The badge reflects the **latest IngestionRun** returned by the backend.

| IngestionRun state | Badge label | Color token | Icon (lucide) |
| --- | --- | --- | --- |
| No run yet | `Not ingested` | neutral | `CircleDashed` |
| `processing` | `Ingesting` | info | `Loader2` (spinning) |
| `succeeded` | `Ingested` | success | `CheckCircle2` |
| `partial` (some rows/records rejected) | `Partially ingested` | warning | `AlertTriangle` |
| `failed` | `Failed` | danger | `XCircle` |

Ingestion panel behavior:

- **Primary path, URL ingestion (S1-BR-019):** the `Ingest reviews` primary button starts ingestion from the target's saved Google Maps URL. The panel shows: `ReviewLens will collect reviews from this target's Google Maps page.`
- **Secondary path, CSV upload (S1-BR-027):** a ghost button / link `Upload a CSV instead` expands the `FileUploadField` below the primary action. It is never the default, never the larger button, and is labelled as the fallback: `Use this if Google Maps reviews can't be collected right now.`
- **While ingesting:** badge = `Ingesting`; both actions disabled; text `Collecting reviews from Google Maps. This can take up to a minute.` (or `Importing reviews from <file name>...`).
- **On success:** success `Alert`: `Ingested <N> reviews from Google Maps.` (or `Imported <N> reviews from <file name>.`) plus timestamp. Reviews panel refreshes.
- **On partial success:** warning `Alert`: `Ingested <N> reviews. <M> records were skipped because they were missing a rating or review text.` Never present a partial run as fully successful.
- **On failure:** danger/warning `Alert` with the mapped message from Section 5.4, timestamp, and a `Try again` button. Existing reviews remain visible.
- Counts (`N`, `M`) always come from the backend's recorded IngestionRun, never from client-side guesses. Never show a success state unless the backend reported success.
- Sprint 1 shows **only** this basic result. Rating averages, distributions, and charts belong to the Sprint 2 Summary tab (S1-BR-026).

---

## 7. Buttons and Actions

### 7.1 Variants

| Variant | Look | Use |
| --- | --- | --- |
| **Primary** | Solid `--color-primary`, white text | The single main action of a page, form, or panel |
| **Secondary** | White surface, `--color-border` border, `--color-text` text | Alternative actions (`Cancel`, `Back`) |
| **Ghost** | No border/background until hover | Low-emphasis actions (`Upload a CSV instead`, overflow menu items) |
| **Destructive** | Solid `--color-danger`, white text | Irreversible actions (delete), only inside a `ConfirmDialog` |
| **Link** | Text in `--color-primary`, underline on hover | Navigation inside text |

### 7.2 Rules

- **One primary button per view region** (page header, form, or panel).
- Labels are **verb first, sentence case, specific**: `Create target`, `Ingest reviews`, `Upload reviews`, `Try again`, `Log out`. Avoid `Submit`, `OK`, `Yes`.
- Sizes: default height 36px; small 32px (inside cards/tables); large 44px (auth pages and mobile primary actions). Minimum touch target 44x44px on mobile.
- **Buttons perform actions; links navigate.** Do not use a button for navigation or a link for a mutation.
- **Disabled buttons** must have a visible reason nearby (helper text or tooltip), e.g. `Ingestion is already running.`
- **Destructive actions** (`DELETE /api/targets/{id}`) always open a `ConfirmDialog` that names the object: `Delete "Joe's Pizza"? This removes the target and all of its reviews. This can't be undone.` Buttons: `Cancel` (secondary, default focus) and `Delete target` (destructive). On success: toast `Target deleted`, navigate to `/dashboard`.
- **Button order:** primary on the right, secondary on the left (desktop). On mobile, stack with primary on top.
- All interactive elements show a visible focus ring: 2px `--color-primary` outline with 2px offset.

---

## 8. Reusable Components

Build these once in `frontend/src/components/ui/` (layout components in `frontend/src/components/layout/`) and reuse them. **Do not create one-off variants on a page.** If a shared component does not support what you need, extend the shared component in the same PR.

| Component | Purpose | Key requirements |
| --- | --- | --- |
| `AppShell` | Header + sidebar + main content for all authenticated pages | Responsive behavior from Section 3.1; shows active target section |
| `AuthLayout` | Centered card layout for auth pages | No sidebar; logo above card |
| `AccountMenu` | Header account dropdown | Shows user email; `Log out` item |
| `ProtectedRoute` | Route guard for authenticated pages | Skeleton while session restores; redirect to `/login` with return path |
| `PageHeader` | Title, optional description, optional primary action | Renders the page's single `h1` |
| `TargetContextHeader` | Workspace identity: name, platform, source, status, created date | Sticky; always visible in workspace |
| `WorkspaceTabs` | Tabs inside the workspace | Sprint 1: Reviews only; keyboard arrow-key navigation |
| `TargetCard` | One target on the dashboard | Whole card clickable; keyboard accessible |
| `PlatformBadge` | Shows `Google Maps` | Same text/icon everywhere |
| `StatusBadge` | Ingestion state | Only states/labels from Section 6.3 |
| `Button` | All buttons | Variants and sizes from Section 7; `loading` prop |
| `TextField` | Label + input + helper + error | `aria-invalid`, `aria-describedby`, required marker; password variant with show/hide |
| `FileUploadField` | CSV picker / drop zone | `.csv` only; shows selected file; inline errors |
| `FormErrorSummary` | Top-of-form error banner | Focusable; summarizes errors |
| `Alert` | Inline banner (success / info / warning / danger) | Icon + title + message + optional action |
| `Toast` | Transient notifications | Single provider at app root; error toasts persist until dismissed |
| `EmptyState` | Empty lists/panels | Icon, title, description, action |
| `Skeleton` | Loading placeholders | Matches content shape |
| `ConfirmDialog` | Confirm destructive actions | Focus trapped; `Esc` cancels; default focus on Cancel |
| `ReviewList` / `ReviewItem` | Persisted reviews in workspace | Rating, text, and available metadata |
| `NotFoundState` | Not-found / no-access state | Single message for both cases (Section 5.4) |

### 8.1 Review display (`ReviewItem`)

- **Rating:** 5-star display in `--color-rating` plus the numeric value as text (`4 out of 5`) for accessibility. Do not rely on star icons alone.
- **Review text:** clamp to 4 lines with a `Show more` toggle; render the original text exactly (no AI rewriting, no HTML injection: render as text, never as raw HTML).
- **Metadata** (when available): reviewer display name, review date in `MMM D, YYYY`, `View on Google Maps` link to the original review. Missing metadata is simply omitted; never show `undefined`, `null`, `N/A`, or placeholder names.
- Reviews panel header shows the persisted count from the API: `Reviews (N)`.

---

## 9. Content and Terminology

Use these terms consistently in UI copy, code names, and docs:

| Use | Don't use |
| --- | --- |
| Analysis target (or "target") | Project, business entry, item |
| Dashboard (the target list page) | Home, targets page |
| Analysis workspace (or "workspace") | Details page, target page |
| Ingest / ingestion (URL path) | Scrape, fetch, crawl |
| Upload a CSV / import (CSV path only) | Ingest a file |
| Review | Comment, feedback item |
| Google Maps (the review platform) | Google, Maps, GMaps |
| Google Maps URL / source URL | Link, endpoint |
| Log in / Log out / Register | Sign in / Sign out / Sign up, Login (as a verb) |

- Dates: `Oct 26, 2026`. Date + time: `Oct 26, 2026, 7:16 PM` in the user's local timezone.
- Numbers: thousands separators (`1,240 reviews`). Correct singular/plural (`1 review`, `2 reviews`).
- Tone: clear, calm, direct. No exclamation marks in errors, no blame (`You entered an invalid URL` becomes `Enter a valid URL...`).

---

## 10. Accessibility Baseline

- All functionality works with keyboard only (Tab, Shift+Tab, Enter, Space, Esc, arrow keys in tabs/menus).
- Logical tab order matching visual order; skip-to-content link in the `AppShell`.
- Semantic HTML first: `button`, `a`, `nav`, `main`, `header`, `form`, `label`. Use ARIA only to fill gaps.
- Every input has a programmatic label. Every image/icon that conveys meaning has a text alternative.
- Dialogs and menus trap/return focus correctly.
- Color contrast meets WCAG AA (Section 4.1). Status never relies on color alone.
- Respect `prefers-reduced-motion`: disable non-essential animation (spinners may remain).

---

## 11. Sprint Scope Guardrails for UI

- **Sprint 1 UI covers:** log in / register / password reset, dashboard, create target, delete target, Analysis Workspace (Reviews tab), URL-initiated ingestion with status, CSV upload as a secondary path, persisted review list, and all error/empty/loading states in this document.
- **URL ingestion is primary (S1-BR-019).** CSV upload is a recovery path only (S1-BR-027); a UI that offers only CSV upload does not satisfy S1-019.
- **Do not build Sprint 2+ UI in Sprint 1:** Summary tab, Ask/AI chat tab, rating charts or distributions, or disabled "coming soon" placeholders. The `POST /api/targets/{id}/ask` endpoint has no Sprint 1 UI.

---

## 12. UI Pull Request Checklist

Copy into the PR description for any UI change and confirm each item:

- [ ] Uses `AppShell`/`AuthLayout`, `PageHeader`, and other shared components; no one-off duplicates.
- [ ] Colors, spacing, and font sizes come from `tokens.css` and the scales in Section 4.
- [ ] One primary action per view region; button labels are verb-first sentence case.
- [ ] Loading, empty, success, and error states are all implemented for new data views.
- [ ] Error messages come from `frontend/src/lib/messages.ts` and follow Section 5.4; no raw FastAPI, Supabase, or exception text displayed.
- [ ] Forms follow Section 5 (labels, required markers, inline errors, preserved input, backend errors shown).
- [ ] No user ID / owner ID sent in request bodies; ownership comes from the auth token.
- [ ] Active target name, `Google Maps` badge, and source URL are visible on every target-scoped screen.
- [ ] Keyboard navigation and visible focus work; inputs labeled; contrast checked.
- [ ] Checked at desktop (1280px), tablet (768px), and mobile (375px) widths.
- [ ] Automated tests cover at least one happy path and one non-happy path (e.g. validation error rendered, failed ingestion shows error and keeps existing reviews).
- [ ] No Sprint 2+ features or fake data introduced.

---

## 13. Instructions for AI Coding Tools

When generating or modifying ReviewLens UI code:

1. Follow this document exactly; do not introduce new colors, font sizes, spacing values, icon libraries, or navigation patterns.
2. Use React function components with TypeScript types for all props. Reuse the components in Section 8; search `frontend/src/components/` before creating a new one.
3. Implement loading, empty, success, and error states for every new data-driven view.
4. Call the backend only through `frontend/src/lib/api/`. Map errors to the messages in Section 5.4/5.5. Never render `error.message` from an exception, HTTP client, FastAPI response, or Supabase directly.
5. Never send `user_id` / `owner_id` from the frontend as proof of ownership.
6. Never render hard-coded sample reviews, ratings, or counts. Never call Google Maps, a review-data provider, or OpenAI from the browser.
7. Render review text as plain text, never as raw HTML.
8. Do not add Sprint 2+ features (Summary, Ask/AI chat, charts) unless the active sprint story requires them.
9. Generated UI code is reviewed and tested to the same standard as human-written code.

---

## Revision History

| Date | Author | Change |
| --- | --- | --- |
| 2026-10-26 | Amreen | Initial version (S1-002) |
| 2026-10-26 | Amreen | Aligned with Sprint 1 Architecture Baseline: React + TypeScript, Supabase Auth screens, Google Maps platform, Dashboard naming, workspace tabs, CSV upload as secondary path, file locations |
