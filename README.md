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

## Testing & Quality Assurance

This project includes a comprehensive test suite for the FastAPI backend and database layers. 
For detailed instructions on how to run, configure, and write tests, please refer to the [Testing Documentation](./backend/tests/testing.md).
