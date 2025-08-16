import boto3
from botocore.exceptions import ClientError
from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def handle_image_upload(project_id, file_obj, existing_images=None):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    # Remove existing images if specified
    if existing_images:
        for image_key in existing_images:
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=image_key)
                print(f'Image removed: {image_key}')
            except ClientError as e:
                print(f'Error removing image {image_key}: {e}')

    # Upload new image
    new_key = f'projects/{project_id}/{file_obj.name}'
    try:
        s3_client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=bucket_name,
            Key=new_key,
            ExtraArgs={'ContentType': file_obj.content_type}
        )
        return new_key
    except ClientError as e:
        print(f'Error uploading image: {e}')
        raise e
