"""
API endpoints for exporting and importing data.
"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.services.export_import_service import ExportImportService, get_export_import_service
from app.core.config import settings

router = APIRouter(prefix="/export-import", tags=["export-import"])

@router.get("/export/research/{research_id}")
async def export_research(
    research_id: int,
    format: str = Query("json", regex="^(json|csv|pdf|docx)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export research data in the specified format.
    
    - **research_id**: ID of the research to export
    - **format**: Export format (json, csv, pdf, docx)
    """
    try:
        service = get_export_import_service(db)
        filepath = await service.export_research(research_id, current_user.id, format)
        
        # Determine the content type based on the format
        content_type = {
            "json": "application/json",
            "csv": "application/zip",  # CSV export is zipped
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }.get(format, "application/octet-stream")
        
        # Get the filename from the path
        filename = os.path.basename(filepath)
        
        return FileResponse(
            filepath,
            media_type=content_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting research: {str(e)}"
        )

@router.post("/import/research")
async def import_research(
    file: UploadFile = File(...),
    format: str = Query("json", regex="^(json|csv|pdf|docx)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import research data from a file.
    
    - **file**: File containing the data to import
    - **format**: Format of the file (json, csv, pdf, docx)
    """
    try:
        # Verify file extension matches the format
        if format == "json" and not file.filename.lower().endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File extension does not match the specified format (expected .json)"
            )
        elif format == "csv" and not file.filename.lower().endswith(('.csv', '.zip')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File extension does not match the specified format (expected .csv or .zip)"
            )
        elif format == "pdf" and not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File extension does not match the specified format (expected .pdf)"
            )
        elif format == "docx" and not file.filename.lower().endswith(('.docx', '.doc')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File extension does not match the specified format (expected .docx or .doc)"
            )
        
        service = get_export_import_service(db)
        result = await service.import_research(file, current_user.id, format)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing research: {str(e)}"
        )

@router.get("/formats")
async def get_supported_formats():
    """Get a list of supported export/import formats."""
    return {
        "export_formats": ["json", "csv", "pdf", "docx"],
        "import_formats": ["json", "csv", "pdf", "docx"],
        "export_dir": settings.EXPORT_DIR
    }
