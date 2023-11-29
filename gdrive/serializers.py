from rest_framework import serializers


class CredentialsSerializer(serializers.Serializer):
    token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_uri = serializers.URLField()
    client_id = serializers.CharField()
    client_secret = serializers.CharField()
    scopes = serializers.ListField(child=serializers.CharField())
    expiry = serializers.CharField()


class RequestFilesSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    mimeType = serializers.CharField()

class RequestDataSerializer(serializers.Serializer):
    credentials = CredentialsSerializer()
    files = RequestFilesSerializer(many=True)
    access_token=serializers.CharField()