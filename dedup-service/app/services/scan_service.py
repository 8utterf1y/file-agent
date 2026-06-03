from sqlalchemy.orm import Session

from app.schemas import FailedFile, ScanResponse
from app.services.dedup_analysis_service import run_dedup_analysis
from app.services.process_service import process_file
from app.sources.local_scanner import scan_local_dir


def scan_and_analyze(db: Session, source_path: str) -> ScanResponse:
    files = scan_local_dir(source_path)
    processed = 0
    skipped = 0
    failed: list[FailedFile] = []

    for item in files:
        try:
            result = process_file(db, item)
            if result.processed:
                processed += 1
            if result.skipped:
                skipped += 1
        except Exception as exc:
            db.rollback()
            failed.append(FailedFile(path=item.path, error=str(exc)))

    cluster_count = run_dedup_analysis(db)
    return ScanResponse(
        source_path=source_path,
        total_files=len(files),
        processed=processed,
        skipped=skipped,
        failed=failed,
        cluster_count=cluster_count,
    )
