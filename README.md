# AI Powered Job Application Tracker
## Overview
The AI-Powered Job Application Tracker is a comprehensive full-stack career management platform designed to help job seekers take control of their job hunt. By combining an intuitive application pipeline tracker with cutting-edge AI integrations, the app automates tedious tasks like resume optimization and cover letter generation—allowing you to land your next role faster and smarter.

## Core Purpose
To eliminate the friction, chaos, and manual work of tracking job applications by centralizing your career pipeline and leveraging artificial intelligence to tailor your professional profile to any job description instantly.

## Tech Stack
* **Frontend:** React,React Router, TypeScript, CSS  
* **Backend:** FastAPI (Python) & PostgreSQL  
* **AI Tools:** Groq API

## Features
1. **User Authentication & Security** Secures user sessions via HTTP-only cookies and JWT tokens to guarantee full data privacy and isolation.
2. **Job Application Pipeline** Provides complete CRUD capabilities to track, update, and manage individual job application statuses.
3. **Search & Filtering** Allows users to instantly narrow down their application records using status categories and keyword text searches.
4. **Dashboard Analytics & Statistics** Aggregates pipeline volume and application metrics at the database level to display quick performance insights at a glance.
5. **Resume Management & Parsing** Extracts text from uploaded PDF resumes to evaluate professional strengths and feedback using AI.
6. **AI Cover Letter Generator** Automatically synthesizes resume data and job descriptions to generate tailored, ready-to-use cover letters.

## Local Development & Deployment

### Running with Docker

The backend includes a Dockerfile for easy containerized deployment:

```bash
# Build the Docker image
cd backend
docker build -t ai-job-tracker-backend .

# Run the container
docker run -d -p 8000:8000 --name job-tracker-backend ai-job-tracker-backend

# Verify it's running
docker logs job-tracker-backend
```

The backend will be available at `http://localhost:8000`.

### Running with Docker Compose (Recommended)

For a complete development environment with PostgreSQL:

```bash
# Start the database and backend services
docker-compose up -d

# The backend will be available at http://localhost:8000
# PostgreSQL will be available at localhost:5432

# Stop the services
docker-compose down
```

This uses the `docker-compose.yml` file which includes both the FastAPI backend and PostgreSQL database.

## Testing & Quality Assurance

This project includes a comprehensive test suite for the FastAPI backend and database layers. 
For detailed instructions on how to configure and run tests, please refer to the [Testing Documentation](./backend/tests/TESTING.md).
