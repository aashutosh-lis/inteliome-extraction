import os
import requests
from decouple import config
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rest_framework import status
from rest_framework.views import APIView
from .serializers import RequestDataSerializer
from .utils import project_return



class ExtractionView(APIView):
    serializer_class = RequestDataSerializer

    def upload(self, access_token, file_name, file_path, file_type):
        files = {"file": (file_name, open(file_path, "rb"), file_type)}
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.post(
            config("FILE_UPLOAD_URL"), headers=headers, files=files
        )
        result = response.json()

        if result.get("status") != 200:
            return
        return result.get("data")

    def download(self, service, id, name, download_path):
        try:
            media_request = service.files().get_media(fileId=id)
            with open(download_path, "wb") as file:
                downloader = MediaIoBaseDownload(file, media_request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}: {name}.")

        except Exception as e:
            print(f"Error downloading {name}: {str(e)}")
            raise

    def list_files(self, service, dir_id):
        results = (
            service.files()
            .list(
                q=f"'{dir_id}' in parents",
                fields="files(id, name, mimeType, md5Checksum)",
            )
            .execute()
        )
        return results.get("files", [])

    def extract_files(self, service, access_token, items):
        successful_files = []
        failed_files = []

        for item in items:
            file_id = item.get("id")
            file_name = item.get("name")
            file_type = item.get("mimeType")

            if "folder" in file_type:
                folder_contents = self.list_files(service, file_id)
                result = self.extract_files(
                    service=service, access_token=access_token, items=folder_contents
                )
                successful_files.extend(result["successful"])
                failed_files.extend(result["failed"])
            else:
                download_path = os.path.join("downloads", file_name)
                try:
                    self.download(
                        service,
                        id=file_id,
                        name=file_name,
                        download_path=download_path,
                    )
                    file_url = self.upload(
                        access_token=access_token,
                        file_name=file_name,
                        file_path=download_path,
                        file_type=file_type,
                    )

                    if not file_url:
                        raise Exception("File url not received")
                    successful_files.append({"name": file_name, "url": file_url})
                except Exception as e:
                    print(f"Error processing {file_name}: {str(e)}")
                    failed_files.append(file_name)

        return {"successful": successful_files, "failed": failed_files}

    def post(self, request, *args, **kwargs):
        request_obj = self.serializer_class(data=request.data)
        print(request.data)
        if request_obj.is_valid():
            credentials_data = request_obj.validated_data["credentials"]
            request_files = request_obj.validated_data["files"]

            print("Request files: ", request_files)
            access_token = request_obj.validated_data["access_token"]

            credentials = Credentials.from_authorized_user_info(credentials_data)
            try:
                drive_service = build("drive", "v3", credentials=credentials)
            except Exception as e:
                return project_return(
                    message="Error",
                    data=None,
                    error=str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            download_result = self.extract_files(
                service=drive_service, access_token=access_token, items=request_files
            )
            return project_return(
                message="Successful",
                data=download_result,
                error=None,
                status=status.HTTP_201_CREATED,
            )
        else:
            return project_return(
                message="Error",
                data=None,
                error="Invalid request body",
                status=status.HTTP_400_BAD_REQUEST,
            )