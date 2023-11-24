import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from gdrive.utils import project_return, credentials_to_dict
from gdrive.serializer import RequestDataSerializer
from minio import Minio
from minio.error import S3Error
from urllib.parse import quote


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
        # For the current user, check if refresh token exists in the database
        # creds = get_creds_from_db()
        # if not (creds and creds.refresh_token):
        #     return Response(
        #         {"error": "no credentials found"}, status=status.HTTP_404_NOT_FOUND
        #     )
        # else:
        #     if creds.valid:
        #         return {"token": creds.token}
        #     else:
        #         creds.refresh(Request())
        #         # save the updated credsntials to db

        #         return {"token": creds.token}
        # if refresh token exists, and is valid, use it to generate an access token
        # if refresh token is not present, return null


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

    def download(self, service, id, name):
        minio_client = Minio(
            "192.168.50.144:9000",
            access_key="minio",
            secret_key="miniopassword",
            secure=False,
        )

        bucket_name = "tests"
        try:
            media_request = service.files().get_media(fileId=id)
            download_path = os.path.join("downloads", f"{id}_{name}")
            with open(download_path, "wb") as file:
                downloader = MediaIoBaseDownload(file, media_request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}.")

                minio_client.fput_object(
                    bucket_name, f"{id}_{name}", f"downloads/{id}_{name}"
                )
                print(f"Uploaded to minio: {name}")
        except S3Error as e:
            print(f"Error uploading file: {e}")
        except Exception as e:
            print(f"Error downloading {name}: {str(e)}")
            raise
        finally:
            os.remove(download_path)

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
                try:
                    self.download(service, file_id, file_name)
                    file_url = (
                        f"http://192.168.50.144:9000/tests/{file_id}_{quote(file_name)}"
                    )
                    successful_files.append(file_url)
                except Exception as e:
                    print(f"Error processing {file_name}: {str(e)}")
                    failed_files.append(file_name)

        return {"successful": successful_files, "failed": failed_files}

    def post(self, request, *args, **kwargs):
        request_obj = self.serializer_class(data=request.data)
        if request_obj.is_valid():
            credentials_data = request_obj.validated_data["credentials"]
            request_files = request_obj.validated_data["files"]
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
