DB-Schema
# Database Schema Design (PostgreSQL)

This document outlines the relational database schema for the AI-Powered Job Application Tracker MVP.

## Entity-Relationship Overview

- **User** 1-to-Many **Job Applications** (`users.id` -> `jobs.user_id`)
- **User** 1-to-Many **Resumes** (`users.id` -> `resumes.user_id`)


## ER diagram

+-----------------------+       +-----------------------+
|        users          |       |        resumes        |
+-----------------------+       +-----------------------+
| PK  id (SERIAL)       |<------| FK  user_id           |
|     email             |       | PK  id (SERIAL)       |
|     hashed_password   |       |     file_name         |
|     created_at        |       |     file_path         |
+-----------------------+       |     parsed_text       |
            |                   |     uploaded_at       |
            | 1                 +-----------------------+
            |
            | 1-to-Many
            |
            | N
+-----------------------+
|         jobs          |
+-----------------------+
| PK  id (SERIAL)       |
| FK  user_id           |
|     company_name      |
|     job_title         |
|     job_description   |
|     status            |
|     application_date  |
|     salary_range      |
|     notes             |
|     created_at        |
|     updated_at        |
+-----------------------+

---

## Tables

### 1. `users`
Stores user authentication and profile data.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / UUID | PRIMARY KEY | Unique identifier for the user |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User's email address for login |
| `hashed_password` | VARCHAR(255) | NOT NULL | Securely hashed password (bcrypt) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

---

### 2. `resumes`
Stores uploaded PDF resume files or their extracted text content for AI processing.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / UUID | PRIMARY KEY | Unique identifier for the resume record |
| `user_id` | INT / UUID | FOREIGN KEY (`users.id`), NOT NULL | Owner of the resume |
| `file_name` | VARCHAR(255) | NOT NULL | Original name of the uploaded PDF file |
| `file_path` | TEXT | NOT NULL | Storage path or URL |
| `parsed_text` | TEXT | NULL | Extracted plain text content parsed from the PDF for OpenAI |
| `uploaded_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when the resume was uploaded |

---

### 3. `jobs` (Job Applications)
Stores the details of each job application tracked by the user.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / UUID | PRIMARY KEY | Unique identifier for the job entry |
| `user_id` | INT / UUID | FOREIGN KEY (`users.id`), NOT NULL | Owner of the job entry |
| `company_name` | VARCHAR(255) | NOT NULL | Name of the hiring company |
| `job_title` | VARCHAR(255) | NOT NULL | Role or position applied for |
| `job_description` | TEXT | NULL | Full text description of the job (used for AI cover letters) |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'Wishlist' | Pipeline stage (Wishlist, Applied, Interviewing, Offer, Rejected) |
| `application_date` | DATE | NULL | Date the application was submitted |
| `salary_range` | VARCHAR(100) | NULL | Optional salary range |
| `notes` | TEXT | NULL | Personal user notes regarding the application |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Entry creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification timestamp |