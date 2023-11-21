import os
from pprint import pprint
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AuthenticationView(APIView):
    def get(self, *args, **kwargs):
        # For the current user, check if refresh token exists in the database
        creds = get_creds_from_db()
        if not (creds and creds.refresh_token):
            return Response(
                {"error": "no credentials found"}, status=status.HTTP_404_NOT_FOUND
            )
        else:
            if creds.valid:
                return {"token": creds.token}
            else:
                creds.refresh(Request())
                # save the updated credsntials to db

                return {"token": creds.token}
        # if refresh token exists, and is valid, use it to generate an access token
        # if refresh token is not present, return null
        return Response({"hello": "authentication"}, status=status.HTTP_200_OK)


class OauthCallbackView(APIView):
    def post(self, request, *args, **kwargs):
        authorization_code = request.data.get("code")
        scopes = request.data.get("scope").split()
        print(f"authorization_code: {authorization_code}")
        print(f"scopes: {scopes}")
        print(os.getcwd())

        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=scopes,
            redirect_uri="postmessage",
        )
        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials
        # TODO: Write to database
        pprint(credentials.token)
        print("-" * 100)
        print("Valid? ", credentials.valid)
        print("Refresh Token? ", credentials.refresh_token)
        credentials.refresh(Request())
        print("-" * 100)
        print(credentials.token)
        return Response(credentials.to_json(), status=status.HTTP_200_OK)


class ExtractionView(APIView):
    def download(self, service, id, name):
        try:
            media_request = service.files().get_media(fileId=id)
            downloadPath = os.path.join("../downloads/", f"{id}_{name}")
            print("downloadPath: ", downloadPath)
            with open(downloadPath, "wb") as file:
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

            print(file_name)

            if "folder" in file_type:
                folder_contents = self.list_files(service, file_id)
                print("Folder contents", folder_contents)
                result = self.download_files(service, folder_contents)
                successful_files.extend(result["successful"])
                failed_files.extend(result["failed"])
            else:
                try:
                    self.download(service, file_id, file_name)
                    successful_files.append(file_name)
                except Exception as e:
                    print(f"Error processing {file_name}: {str(e)}")
                    failed_files.append(file_name)

        return {"successful": successful_files, "failed": failed_files}

    def post(self, request, *args, **kwargs):
        request_files = request.data

        credentials = Credentials.from_authorized_user_file("../credentials.json")
        try:
            drive_service = build("drive", "v3", credentials=credentials)
        except:
            response_data = {"error": "could not initialize service"}
            return response_data, 400

        download_result = self.download_files(drive_service, request_files)
        return Response(download_result, status=status.HTTP_200_OK)
