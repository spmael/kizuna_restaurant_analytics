from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import DataUpload
from data_engineering.pipelines.initial_load_pipeline import DataProcessingPipeline
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_data_upload(self, upload_id):
    """Celery task to process a data upload"""
    try:
        # Get Upload Instance
        upload = DataUpload.objects.get(id=upload_id)
        
        logger.info(f"Starting data processing for upload {upload_id}")
        
        # Create and run pipeline
        pipeline = DataProcessingPipeline(upload)
        success = pipeline.process()
        
        if success:
            logger.info(f"Data processing completed successfully for upload {upload_id}")
            return {
                'status': 'success',
                'upload': upload_id,
                'processed_records': upload.processed_records,
                'error_records': upload.error_records,
            }
            
        else:
            logger.error(f"Data processing failed for upload {upload_id}")
            return {
                'status': 'failed',
                'upload': upload_id,
                'error_records': upload.error_records,
            }
    except DataUpload.DoesNotExist:
        error_message = f"Upload {upload_id} does not exist"
        raise Exception(error_message)
    
    except Exception as e:
        logger.error(f"Task failed for upload {upload_id}: {str(e)}")
        
        # Update upload status on failure
        try:
            upload = DataUpload.objects.get(id=upload_id)
            upload.status = 'failed'
            upload.end_processing_at = timezone.now()
            upload.save()
        except:
            pass
            
        raise self.retry(exc=e)

@shared_task
def clean_up_old_uploads():
    """Celery task to clean up old uploaded files and records"""
    
    from datetime import timedelta
    from django.utils import timezone
    import os
    
    # Delet uploaded records older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    old_uploads = DataUpload.objects.filter(created_at__lt=cutoff_date)
    
    delete_files = 0
    deleted_records = 0
    
    for upload in old_uploads:
        try:
            # Delete physiclal file
            if upload.file and os.path.exists(upload.file.path):
                os.remove(upload.file.path)
                delete_files += 1
                
        except Exception as e:
            logger.warning(f"Could not delete file {upload.file.path}: {str(e)}")
            
        # Delete records
        upload.delete()
        deleted_records += 1
        
    logger.info(f"Cleaned up completed - Deleted: {deleted_records} old uploads and {delete_files} files")
    
    return {
        'deleted_records': deleted_records,
        'deleted_files': delete_files
    }
    