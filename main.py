from datetime import date, datetime
from typing import Optional

from psycopg2.extras import RealDictCursor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database import get_connection


app = FastAPI(
    title="JobTrack API",
    description="AWS-hosted job application tracking API",
    version="1.0.0",
)


class JobCreate(BaseModel):
    company: str
    role: str
    status: str = "Applied"
    applied_date: Optional[date] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


@app.get("/")
def home():
    return {
        "message": "JobTrack API is running!",
        "status": "success",
    }


@app.get("/health")
def health():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )


@app.get("/jobs")
def get_jobs():
    conn = get_connection()

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT id, company, role, status,
                   applied_date, job_url, notes, created_at
            FROM jobs
            ORDER BY id;
            """
        )

        jobs = cursor.fetchall()

        return {
            "count": len(jobs),
            "jobs": jobs,
        }

    finally:
        cursor.close()
        conn.close()


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT id, company, role, status,
                   applied_date, job_url, notes, created_at
            FROM jobs
            WHERE id = %s;
            """,
            (job_id,),
        )

        job = cursor.fetchone()

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        return job

    finally:
        cursor.close()
        conn.close()


@app.post("/jobs")
def create_job(job: JobCreate):
    conn = get_connection()

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            INSERT INTO jobs
                (company, role, status, applied_date, job_url, notes)
            VALUES
                (%s, %s, %s, COALESCE(%s, CURRENT_DATE), %s, %s)
            RETURNING id, company, role, status,
                      applied_date, job_url, notes, created_at;
            """,
            (
                job.company,
                job.role,
                job.status,
                job.applied_date,
                job.job_url,
                job.notes,
            ),
        )

        new_job = cursor.fetchone()
        conn.commit()

        return new_job

    finally:
        cursor.close()
        conn.close()


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM jobs WHERE id = %s RETURNING id;",
            (job_id,),
        )

        deleted = cursor.fetchone()

        if deleted is None:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        conn.commit()

        return {
            "message": "Job deleted",
            "id": deleted[0],
        }

    finally:
        cursor.close()
        conn.close()

