from pydantic import BaseModel, validator


class UpdateFileRequest(BaseModel):
    file_name: str