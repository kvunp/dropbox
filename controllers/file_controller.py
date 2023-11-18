import json
from fastapi import File, Header, UploadFile, HTTPException, APIRouter
from datetime import datetime
import os
import uuid
from fastapi.responses import FileResponse
from pymongo import MongoClient, ReturnDocument
from bson.json_util import dumps

file_router = APIRouter()

client = MongoClient('mongodb://127.0.0.1:27017/dropbox') # TODO: move string to env
db = client['file_data'] # TODO: move db name to env
files_collection = db['files'] # TODO: move col name to env
LOCAL_STORAGE_PATH = '/Users/mogili.reddy/Documents/dropbox/uploads' # TODO: move string to env

@file_router.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Header(...)):
    file_id = str(uuid.uuid4())
    extension = os.path.splitext(file.filename)[1]
    filename_with_extension = f"{file_id}{extension}"
    file_location = os.path.join(LOCAL_STORAGE_PATH, filename_with_extension)
    
    try:
        with open(file_location, "wb") as file_object:
            content = await file.read()
            file_object.write(content)
        file_size = os.path.getsize(file_location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating file content: {e}")

    file_metadata = {
        "file_id": file_id,
        "user_id": user_id,
        "file_name": file.filename,
        "storage_name": filename_with_extension,
        "created_at": datetime.utcnow(),
        "size": file_size,
        "file_type": file.content_type
    }
    files_collection.insert_one(file_metadata)
    
    return {"message": "File uploaded successfully."}

@file_router.get("/read/{file_id}")
async def read_file(file_id: str, user_id: str = Header(...)):
    file_data = files_collection.find_one({"file_id": file_id, "user_id": user_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found or access denied.")

    file_location = os.path.join(LOCAL_STORAGE_PATH, file_data['storage_name'])
    if os.path.exists(file_location):
        return FileResponse(path=file_location, filename=file_data['file_name'])
    else:
        raise HTTPException(status_code=404, detail="File not found on server.")
    
@file_router.post("/update/{file_id}")
async def update_file(
    file_id: str, 
    file: UploadFile = File(None), 
    # new_file_name: str = None,
    user_id: str = Header(...),
):
    file_data = files_collection.find_one({"file_id": file_id, "user_id": user_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found or access denied.")

    file_metadata = files_collection.find_one({"file_id": file_id})
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    if file:
        new_extension = os.path.splitext(file.filename)[1]
        new_storage_name = f"{file_id}{new_extension}"
        file_location = os.path.join(LOCAL_STORAGE_PATH, new_storage_name)
        try:
            with open(file_location, "wb") as file_object:
                content = await file.read()
                file_object.write(content)
            file_size = os.path.getsize(file_location)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error occurred while writing file: {e}")
    else:
        file_location = os.path.join(LOCAL_STORAGE_PATH, file_metadata['storage_name'])
        file_size = file_metadata['size']

    # TODO: Update the metadata
    updated_metadata = {}
    # if new_file_name:
    #     updated_metadata['file_name'] = new_file_name
    if file:
        updated_metadata['file_name'] = file.filename
        updated_metadata['storage_name'] = new_storage_name
        updated_metadata['size'] = file_size
        updated_metadata['file_type'] = file.content_type
    updated_metadata['last_updated'] = datetime.utcnow()

    update_result = files_collection.find_one_and_update(
        {"file_id": file_id},
        {"$set": updated_metadata},
        return_document=ReturnDocument.AFTER
    )

    if update_result is None:
        raise HTTPException(status_code=404, detail="File not found.")

    updated_metadata.pop('_id', None)
    return {"message": "File updated successfully.", "updated_metadata": updated_metadata}

@file_router.post("/delete/{file_id}")
async def delete_file(file_id: str, user_id: str = Header(...)):
    file_data = files_collection.find_one({"file_id": file_id, "user_id": user_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    
    file_location = os.path.join(LOCAL_STORAGE_PATH, file_data['storage_name'])
    if os.path.exists(file_location):
        try:
            os.remove(file_location)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
    else:
        raise HTTPException(status_code=404, detail="File not found")

    delete_result = files_collection.delete_one({"file_id": file_id, "user_id": user_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete file metadata.")

    return {"message": "File deleted successfully"}

@file_router.get("/files")
async def list_files(user_id: str = Header(...)):
    try:
        files_cursor = files_collection.find({"user_id": user_id}, {'_id': 0})
        files_data = list(files_cursor)
        files_json = dumps(files_data)
        files_list = json.loads(files_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

    return {"files": files_list}