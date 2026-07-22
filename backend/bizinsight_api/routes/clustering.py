"""
Clustering routes — kick off clustering as a background job, poll status, get results.
Wraps the existing clustering/run_clustering.py without modification.
"""

import os
import uuid
import threading
from fastapi import APIRouter, HTTPException, Depends

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
from database import fetch_feedback
from bizinsight_api.routes.auth import get_current_user
from bizinsight_api.models.schemas import (
    ClusteringRequest, ClusteringJobStatus, ClusteringResult, ClusterItem
)

router = APIRouter(prefix="/api/clustering", tags=["Clustering"])

# In-memory job store (sufficient for single-server deployment)
_jobs: dict = {}

# Load embedding model once at module level (cached by sentence-transformers)
_embedding_model = None
_model_lock = threading.Lock()


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:
                from sentence_transformers import SentenceTransformer
                model_path = os.path.join(
                    os.path.dirname(__file__), '..', '..', 'models', 'finetuned_complaint_model_final'
                )
                if os.path.exists(model_path):
                    _embedding_model = SentenceTransformer(model_path)
                else:
                    _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _run_clustering_job(job_id: str, reviews: list, mode: str):
    """Execute clustering in a background thread and store results."""
    try:
        from clustering.run_clustering import run_pipeline
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["message"] = "Loading embedding model..."

        embedding_model = _get_embedding_model()

        _jobs[job_id]["message"] = f"Clustering {len(reviews)} reviews..."

        dynamic_min_topic_size = max(3, len(reviews) // 5)
        result = run_pipeline(
            reviews,
            embedding_model,
            min_topic_size=dynamic_min_topic_size,
            similarity_threshold=0.4,
            verbose=False,
            mode=mode,
        )

        if result["success"]:
            clusters = [
                ClusterItem(
                    id=c.get("id", 0),
                    name=c["name"],
                    count=c["count"],
                    percentage=round(c["percentage"], 1),
                    example_reviews=c.get("example_reviews", [])[:3],
                )
                for c in result["clusters"]
            ]

            _jobs[job_id]["result"] = ClusteringResult(
                success=True,
                message=result["message"],
                total_reviews=result["total_reviews"],
                n_clusters=result["n_clusters"],
                noise_percentage=round(result["noise_percentage"], 1),
                clusters=clusters,
            )
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["message"] = result["message"]
        else:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["message"] = result["message"]

    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["message"] = f"Clustering failed: {str(e)}"


@router.post("/run", response_model=ClusteringJobStatus)
def start_clustering(
    req: ClusteringRequest,
    current_user: dict = Depends(get_current_user),
):
    """Kick off clustering as a background job. Returns a job_id to poll."""
    data = fetch_feedback(user_id=current_user["id"])
    if not data:
        raise HTTPException(status_code=404, detail="No reviews found. Upload some first.")

    df = pd.DataFrame(data, columns=["review", "sentiment", "date"])

    if req.mode == "negative":
        selected = df[df["sentiment"] < 0]["review"].tolist()
    else:
        selected = df[df["sentiment"] > 0]["review"].tolist()

    if len(selected) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Only {len(selected)} {req.mode} reviews. Need at least 10.",
        )

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending",
        "message": "Job queued...",
        "result": None,
    }

    thread = threading.Thread(
        target=_run_clustering_job,
        args=(job_id, selected, req.mode),
        daemon=True,
    )
    thread.start()

    return ClusteringJobStatus(job_id=job_id, status="pending", message="Job queued...")


@router.get("/status/{job_id}", response_model=ClusteringJobStatus)
def clustering_status(job_id: str):
    """Poll for job status."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = _jobs[job_id]
    return ClusteringJobStatus(
        job_id=job_id,
        status=job["status"],
        message=job.get("message"),
    )


@router.get("/results/{job_id}", response_model=ClusteringResult)
def clustering_results(job_id: str):
    """Get results for a completed clustering job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = _jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not complete yet (status: {job['status']}). Poll /status/{job_id} first.",
        )

    return job["result"]
