import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rest_framework import status
from rest_framework.views import APIView
from gdrive.utils import project_return, credentials_to_dict
from gdrive.serializer import RequestDataSerializer

from decouple import config
import requests


class AuthenticationView(APIView):
    def get(self, *args, **kwargs):
        if os.path.exists("credentials.json"):
            scopes = "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.metadata.readonly"
            credentials = Credentials.from_authorized_user_file(
                "credentials.json", scopes=scopes
            )
            return project_return(
                message="Successful",
                data=credentials_to_dict(credentials),
                error=None,
                status=status.HTTP_200_OK,
            )
        return project_return(
            message="Successful", data=None, status=status.HTTP_200_OK, error=None
        )


class OauthCallbackView(APIView):
    def post(self, request, *args, **kwargs):
        authorization_code = request.data.get("code")
        scopes = request.data.get("scope").split()

        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=scopes,
            redirect_uri="postmessage",
        )
        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials

        return project_return(
            message="Successful",
            data=credentials_to_dict(credentials),
            status=status.HTTP_200_OK,
            error=None,
        )


class ExtractionView(APIView):
    serializer_class = RequestDataSerializer

    def upload(self, access_token, file_name, file_path, file_type):
        files = ["file", (file_name, open(file_path, "rb"), file_type)]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.post(
            config("FILE_UPLOAD_URL"), headers=headers, files=files
        )

        result = response.json()
        if result.get("result") != 200:
            return
        return result.get("data")

    def download(self, service, id, name, download_path):
        try:
            file_name = f"{id}_{name}"
            download_path = os.path.join("downloads", file_name)
            media_request = service.files().get_media(fileId=id)
            with open(download_path, "wb") as file:
                downloader = MediaIoBaseDownload(file, media_request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}.")

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

    def download_files(self, service, items):
        successful_files = []
        failed_files = []

        for item in items:
            file_id = item.get("id")
            file_name = item.get("name")
            file_type = item.get("mimeType")

            if "folder" in file_type:
                folder_contents = self.list_files(service, file_id)
                result = self.download_files(service, folder_contents)
                successful_files.extend(result["successful"])
                failed_files.extend(result["failed"])
            else:
                download_path = os.path.join("downloads", file_name)
                try:
                    self.download(
                        service,
                        file_id=file_id,
                        file_name=file_name,
                        download_path=download_path,
                    )
                    file_url = self.upload(
                        "",
                        file_name=file_name,
                        file_path=download_path,
                        file_type=file_type,
                    )
                    successful_files.append(file_url)
                except Exception as e:
                    print(f"Error processing {file_name}: {str(e)}")
                    failed_files.append(file_name)
                finally:
                    os.remove(download_path)

        return {"successful": successful_files, "failed": failed_files}

    def post(self, request, *args, **kwargs):
        request_obj = self.serializer_class(data=request.data)
        if request_obj.is_valid():
            credentials_data = request_obj.validated_data["credentials"]
            request_files = request_obj.validated_data["files"]
            access_token = request_obj.validated_data["access_token"]

            print("=" * 100)
            print(access_token)
            print("=" * 100)
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
            download_result = self.download_files(drive_service, request_files)
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
