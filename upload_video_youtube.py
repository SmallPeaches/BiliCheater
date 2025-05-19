import json
import logging
import httplib2
import os
import random
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
import yaml
import logging

logging.basicConfig(level=logging.DEBUG)

class youtubev3():
    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1
    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 10000
    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, ConnectionResetError)
    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
    YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    MISSING_CLIENT_SECRETS_MESSAGE = f"""
    WARNING: Please configure OAuth 2.0

    with information from the API Console
    https://console.cloud.google.com/

    For more information about the client_secrets.json file format, please visit:
    https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
    """

    VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

    def __init__(
        self,
        client_secrets,
        account:str=None,
        credential_args:list=None, 
        **kwargs
    ) -> None:
        if not os.path.exists(client_secrets):
            raise FileNotFoundError(f"Client secrets file not found: {client_secrets}")
        self.client_secrets = client_secrets

        if account.endswith('.json'):
            self.account_oauth = account
        else:
            self.account_oauth = f'.login_info/{account}.json'

        self.logger = logging
        self.auth_flags = argparser.parse_args(args=credential_args)

        self._get_authenticated_service()

    def _get_authenticated_service(self):
        storage = Storage(self.account_oauth)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            flow = flow_from_clientsecrets(self.client_secrets,
                                        scope=self.YOUTUBE_UPLOAD_SCOPE,
                                        message=self.MISSING_CLIENT_SECRETS_MESSAGE)
            credentials = run_flow(flow, storage, self.auth_flags)

        return build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION,
                    credentials=credentials)

    def _resumable_upload(self, insert_request):
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if 'id' in response:
                    print(response)
                    return True, str(response['id'])
                else:
                    return False, "The upload failed with an unexpected response: %s" % response
            except HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
                else:
                    raise
            except self.RETRIABLE_EXCEPTIONS as e:
                error = f"A retriable error occurred: {e}"

            if error is not None:
                self.logger.error(error)
                retry += 1
                if retry > self.MAX_RETRIES:
                    return False, error

                max_sleep = min(5*retry, 60)
                sleep_seconds = random.random() * max_sleep
                self.logger.debug(f"Sleeping {sleep_seconds} seconds and then retrying...")
                time.sleep(sleep_seconds)
            else:
                retry = 0
        
        return False, 'Unknown error occurred.'

    def upload_one(self, 
        video: str,
        title: str='',
        desc: str='',
        tag: str=None,
        category: str="20",
        privacy: str="public",
        raw_upload_body: str=None,
        **kwargs,
    ):
        youtube = self._get_authenticated_service()

        if raw_upload_body:
            body = json.loads(raw_upload_body)
        else:
            tags = tag.split(",") if tag else None
            body = {
                "snippet": {
                    "title": title,
                    "description": desc,
                    "tags": tags,
                    "categoryId": str(category)
                },
                "status": {
                    "privacyStatus": privacy
                }
            }

        self.logger.debug(f"Upload config: {video}-{body}")

        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video, chunksize=-1, resumable=True)
        )

        return self._resumable_upload(insert_request)


if __name__ == '__main__':
    with open('UPLOAD_VIDEO_YTB.yml','r',encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    VIDEO = config['videos']
    if isinstance(VIDEO, str):
        if os.path.isfile(VIDEO):
            VIDEO = [VIDEO]
        elif os.path.isdir(VIDEO):
            VIDEO = [os.path.join(VIDEO, x) for x in os.listdir(VIDEO)]
            VIDEO = sorted(VIDEO)
        else:
            raise ValueError('Invalid video path.')
    
    VIDEO = [x for x in VIDEO if x]
    ytb = youtubev3(**config)
    for video in VIDEO:
        print(f'Uploading {video}...')
        status, message = ytb.upload_one(video, **config)
        if status:
            print(f'Upload success: https://www.youtube.com/watch?v={message}')
        else:
            print(f'Upload failed: {message}')
