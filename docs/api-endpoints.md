# API Endpoints Documentation

## 1. Overview
- **Base URL:** `https://api.yourdomain.com/v1`
- **Authentication:** Protected endpoints require a JSON Web Token (JWT) passed via the header: `Authorization: Bearer <token>`

---

## 2. Route Summary

| Endpoint Category | Method & Route | Description / Purpose | Request Payload | Response Type |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication** | `POST /api/auth/register` | Registers a new user account | `email`, `password` | Created user object |
| **Authentication** | `POST /api/auth/login` | Authenticates user & issues session token | `username` (email), `password` | JWT `access_token` |
| **Job Tracking** | `GET /api/jobs` | Fetches all tracked jobs for current user | *None (Token required)* | JSON array of jobs |
| **Job Tracking** | `POST /api/jobs` | Creates a new job application entry | `company_name`, `job_title`, etc. | Created job object |
| **Job Tracking** | `PUT /api/jobs/{job_id}` | Updates specific fields of an application | Fields to change | Updated job object |
| **Job Tracking** | `DELETE /api/jobs/{job_id}` | Deletes a job application record | *None (Token required)* | `204 No Content` |
| **Resumes & AI** | `POST /api/resumes/upload` | Uploads and parses a PDF resume file | Multipart Form Data (`file`) | Resume metadata object |
| **Resumes & AI** | `POST /api/ai/cover-letter` | Generates a tailored AI cover letter | `job_id`, `resume_id` | Generated text string |

---

## 3. Interactive Documentation
For detailed request schemas, payload validation rules, parameter data types, and live endpoint testing, refer to the auto-generated Swagger UI at `/docs` when your FastAPI backend server is running.