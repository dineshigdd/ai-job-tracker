# Low Fidelity Wireframes

## Wireframe Mapping to APIs
- Auth View: Interacts with token endpoints (POST /auth/login, POST /users/, POST /users/login).

- Dashboard View: Fetches summary data via GET /dashboard/stats and lists entries via GET /jobs/.

- Resume View: Uploads documents via multipart form data to POST /resumes/analyze.

- Profile View: Manages user configuration via PUT /users/me and removal via DELETE /users/me.
---

## Authentication View (POST /auth/login, POST /users/, POST /users/login)
```
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|                                     +-----------------------+                                     |
|                                     |      [Logo]           |                                     |
|                                     |    JobTracker AI      |                                     |
|                                     +-----------------------+                                     |
|                                     | Sign in to your account|                                    |
|                                     |                       |                                     |
|                                     | [ ! ] Invalid credentials (error alert banner)              |
|                                     |                       |                                     |
|                                     | Email Address         |                                     |
|                                     | [ user@example.com  ] |                                     |
|                                     |                       |                                     |
|                                     | Password              |                                     |
|                                     | [ *************** ]   |                                     |
|                                     |                       |                                     |
|                                     | [   Sign In (Loading) ] |                                   |
|                                     |                       |                                     |
|                                     | Don't have an account?|                                     |
|                                     | [ Register here ]     |                                     |
|                                     +-----------------------+                                     |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

## Main Dashboard & Analytics Overview (/dashboard/stats)
Focus: High-level metrics powered by GET /dashboard/stats, quick actions, and sidebar navigation.
```
+---------------------------------------------------------------------------------------------------+
| 🚀 JobTracker AI            [Search applications...]                   (🔔)  [ Avatar v ] (/users/me) |
+------------------+--------------------------------------------------------------------------------+
|                  |                                                                                |
| 📊 Dashboard     |  Welcome back, Sarah!                                                          |
| 💼 Jobs List     |                                                                                |
| 📄 Resume AI     |  +------------------------+  +------------------------+                        |
| ⚙️ Profile       |  | Total Applications     |  | Interviews Scheduled   |                        |
|                  |  |          24            |  |           5            |                        |
|                  |  +------------------------+  +------------------------+                        |
|                  |  +------------------------+  +------------------------+                        |
|                  |  | Offers Received        |  | Response Rate (%)      |                        |
|                  |  |          2             |  |         33.3%          |                        |
|                  |  +------------------------+  +------------------------+                        |
|                  |                                                                                |
|                  |  Quick Actions:                                                                |
|                  |  [ 📄 Upload & Analyze New Resume ] -> triggers POST /resumes/analyze           |
|                  |  [ + Track New Job Application    ] -> triggers POST /jobs/                 |
|                  |                                                                                |
|                  |  Recent Applications Preview                                                   |
|                  |  +--------------------------------------------------------------------------+  |
|                  |  | Google - Software Engineer | Interviewing | Applied 3 days ago           |  |
|                  |  | Stripe - Frontend Dev      | Applied      | Applied 5 days ago           |  |
|                  |  +--------------------------------------------------------------------------+  |
+------------------+--------------------------------------------------------------------------------+
```
## Resume Optimization View (/resumes/analyze)
Focus: Two-column split interface allowing users to upload resumes and query OpenAI integration via FastAPI.
```
+------------------+--------------------------------------------------------------------------------+
| 🚀 JobTracker AI |  AI Resume Analyzer & ATS Matcher                     [ Avatar v ]             |
+------------------+--------------------------------------------------------------------------------+
|                  |                                                                                |
| 📊 Dashboard     |  +----------------------------------+  +------------------------------------+  |
| 💼 Jobs List     |  | Left Column: Input               |  | Right Column: AI Results           |  |
| 📄 Resume AI     |  |                                  |  |                                    |  |
| ⚙️ Profile       |  | [ Drag & Drop PDF / DOCX here ]  |  | ATS Match Score                    |  |
|                  |  |    or [ Browse Files ]           |  |      ( O ) 85% Match               |  |
|                  |  |                                  |  |                                    |  |
|                  |  | Target Job Description (Optional)|  | Key Findings / Feedback:           |  |
|                  |  | [ Paste job description text...  |  | - Strong Python & FastAPI matching |  |
|                  |  |   to match keywords against... ] |  | - Missing: Docker compose, AWS     |  |
|                  |  |                                  |  |                                    |  |
|                  |  | [ Analyze Resume (POST /resumes/analyze) ]| | AI Suggestions:                    |  |
|                  |  |                                  |  | - Highlight cloud container deploy |  |
|                  |  +----------------------------------+  +------------------------------------+  |
+------------------+--------------------------------------------------------------------------------+
```
## User Profile View (/users/me)
Focus: Account setting modifications (PUT /users/me) and safety precautions (DELETE /users/me).
```
+------------------+--------------------------------------------------------------------------------+
| 🚀 JobTracker AI |  Account Settings & Profile                           [ Avatar v ]             |
+------------------+--------------------------------------------------------------------------------+
|                  |                                                                                |
| 📊 Dashboard     |  Profile Information (PUT /users/me)                                           |
| 💼 Jobs List     |  +--------------------------------------------------------------------------+  |
| 📄 Resume AI     |  | Full Name: [ Sarah Jenkins        ]                                      |  |
| ⚙️ Profile       |  | Email:     [ sarah@example.com    ] (Verified)                           |  |
|                  |  | Role:      [ Full Stack Developer ]                                      |  |
|                  |  |                                                [ Save Changes ]      |  |
|                  |  +--------------------------------------------------------------------------+  |
|                  |                                                                                |
|                  |  Danger Zone (DELETE /users/me)                                                |  |
|                  |  +--------------------------------------------------------------------------+  |
|                  |  | Delete Account                                                           |  |
|                  |  | Once you delete your account, all data and tracked jobs will be wiped.     |  |
|                  |  |                                             [ Delete Account Button ]    |  |
|                  |  +--------------------------------------------------------------------------+  |
+------------------+--------------------------------------------------------------------------------+
```