from __future__ import print_function
import pickle
import os
import io
import shutil
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.cloud import vision

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive'
]

service = None

def initialize():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    global service
    service = build('drive', 'v3', credentials=creds)

def get_folder_id(folder_name):
    results = service.files().list(
        # q="'1-7Ee_0LfGxchqVulbYEqHI1LKuLnZx6v' in parents",
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    files = results['files']
    print(f"Matching folders:\n{files}")
    if len(files) == 0:
        raise ValueError("No folder with the given name found. Check your spelling and ensure the folder exists.")
    if len(files) > 1:
        raise ValueError("Found multiple folders with the provided name. Please provide unique names to your folder.")
    
    return files[0]['id']

def get_images_in_folder(folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png')",
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print("No images found in the specified folder. Make sure the images are in the JPG or PNG formats")
    else:
        print('Images in folder:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
    
    return items

def download_image(folder_id, image_id, image_name):
    request = service.files().get_media(fileId=image_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    fh.seek(0)
    with open(f"./{folder_id}/{image_name}", "wb") as f:
        shutil.copyfileobj(fh, f)
    print(f"Finished downloading file {image_name}")


def download_images(folder_id, images_in_folder):
    print(f"Creating folder: {folder_id}")
    os.mkdir(f"./{folder_id}")
    for image in images_in_folder:
        download_image(folder_id, image['id'], image['name'])


def create_folder(folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': ['1X79aShzcaYiiE4QL1JKEPZs-fmhQiW_M']
    }
    file = service.files().create(body=file_metadata,
                                        fields='id').execute()
    print ('Folder ID: %s' % file.get('id'))


def detect_document(folder_id, image_name):
    """Detects document features in an image."""
    client = vision.ImageAnnotatorClient()

    with io.open(f"./{folder_id}/{image_name}", 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
    
    image_text = response.full_text_annotation.text
    print(image_text)
    return image_text

def run_detection(folder_id, images_in_folder):
    complete_text = ""
    image_to_text_mappings = []
    for image in images_in_folder:
        image_text = detect_document(folder_id, image['name'])
        image_to_text_mappings.append({
            'image_name': image['name'],
            'image_id': image['id'],
            'image_text': image_text
        })
    complete_text = ''.join([image_mapping['image_text'] for image_mapping in image_to_text_mappings])
    print("Finished Recognition")
    print(complete_text)


def main():
    initialize()
    if(len(sys.argv) != 2):
        raise ValueError("You need to pass in the folder name in which to run recognition.")
    folder_id = get_folder_id(sys.argv[1])
    images_in_folder = get_images_in_folder(folder_id)
    download_images(folder_id, images_in_folder)
    run_detection(folder_id, images_in_folder)

if __name__ == '__main__':
    main()