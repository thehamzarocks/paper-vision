from __future__ import print_function
import pickle
import os
import io
import shutil
import sys
import json
from googleapiclient.discovery import build
from mimetypes import MimeTypes 
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.cloud import vision
from autocorrect import Speller

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive'
]

service = None
spell = Speller(only_replacements=True)

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

def download_image(folder_name, image_id, image_name):
    request = service.files().get_media(fileId=image_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    fh.seek(0)
    with open(f"./{folder_name}/{image_name}", "wb") as f:
        shutil.copyfileobj(fh, f)
    print(f"Finished downloading file {image_name}")


def download_images(folder_name, images_in_folder):
    print(f"Creating folder: {folder_name}")
    os.mkdir(f"./{folder_name}")
    for image in images_in_folder:
        download_image(folder_name, image['id'], image['name'])


def create_folder(folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': ['1X79aShzcaYiiE4QL1JKEPZs-fmhQiW_M']
    }
    file = service.files().create(body=file_metadata,
                                        fields='id').execute()
    print ('Folder ID: %s' % file.get('id'))


def detect_document(folder_name, image_name):
    """Detects document features in an image."""
    client = vision.ImageAnnotatorClient()

    with io.open(f"./{folder_name}/{image_name}", 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
    
    image_text = spell(response.full_text_annotation.text)
    return image_text
    

def run_detection(folder_name, images_in_folder):
    print("Running Recognition, please wait...")
    complete_text = ""
    image_to_text_mappings = []
    for image in images_in_folder:
        image_text = detect_document(folder_name, image['name'])
        image_to_text_mappings.append({
            'image_name': image['name'],
            'image_id': image['id'],
            'image_text': image_text
        })
    complete_text = ''.join([image_mapping['image_text'] for image_mapping in image_to_text_mappings])
    print("Finished Recognition")
    print(complete_text)
    return {
        'type': 'image_to_text_mappings',
        'version': 1,
        'folder': folder_name,
        'complete_text': complete_text,
        'image_to_text_mappings': image_to_text_mappings
    }

def save_image_text_data(folder_id, folder_name, image_text_data):
    print(f"Writing image text data for {folder_name}")
    file_path = f"./{folder_name}/{folder_name}.image_text_data.json"
    with open(file_path, "w") as f:
        f.write(json.dumps(image_text_data))
    print(f"Uploading image text data for {folder_name} to Drive")
    name = file_path.split('/')[-1]
    mimetype = MimeTypes().guess_type(name)[0]
    file_metadata = {
        'name': name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype=mimetype)
    file = service.files().create(
                body=file_metadata, media_body=media, fields='id').execute()
    print("File uploaded to Drive")

def run_recognition_command(folder_name):
    folder_id = get_folder_id(folder_name)
    images_in_folder = get_images_in_folder(folder_id)
    images_in_folder.sort(key=lambda image: image['name'])
    download_images(folder_name, images_in_folder)
    image_text_data = run_detection(folder_name, images_in_folder)
    save_image_text_data(folder_id, folder_name, image_text_data)


def get_image_text_data_files():
    results = service.files().list(
        q=f"name contains 'image_text_data.json'",
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print("No image text data found, try running recognition on your image folders first")
    else:
        print('Image text data:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
    return items

def download_image_text_data_file(id, name):
    request = service.files().get_media(fileId=id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    fh.seek(0)
    with open(f"./image_text_data/{name}", "wb") as f:
        shutil.copyfileobj(fh, f)
    print(f"Finished downloading file {name}")


def download_image_text_data_files(image_text_data_list):
    os.mkdir(f"./image_text_data")
    for image_text_data_file in image_text_data_list:
        download_image_text_data_file(image_text_data_file['id'], image_text_data_file['name'])

def get_mappings(image_text_data_files_list):
    print("Searching files for match")
    mappings = []
    for data_file in image_text_data_files_list:
        file_name = data_file['name']
        file_path = f"./image_text_data/{file_name}"
        with open(file_path, "r") as f:
            mappings.append(json.loads(f.read()))
    return mappings

def search_in_mappings(mappings, query):
    for mapping in mappings:
        complete_text = mapping['complete_text']
        index = complete_text.find(query)
        if(index == -1):
            continue
        print(f"Found in {mapping['folder']}")
    


def run_search_command(query):
    print("Running search")
    image_text_data_files_list = get_image_text_data_files()
    download_image_text_data_files(image_text_data_files_list)
    mappings = get_mappings(image_text_data_files_list)
    search_in_mappings(mappings, query)






def main():
    initialize()
    if(len(sys.argv) < 2):
        raise ValueError("You need to pass in the command: r - recognize, s - search")

    command = sys.argv[1]
    if(len(sys.argv) < 3):
        if (command == 'r'):
            raise ValueError("You need to specify the folder name on which to run recognition")
        if (command == 's'):
            raise ValueError("You need to specify the search query")
        else:
            raise ValueError("You need to specify a command and its parameter")
    param = sys.argv[2]
    if(command == 'r'):
        folder_name = param
        run_recognition_command(folder_name)
    elif(command == 's'):
        query = param
        run_search_command(query)
    else:
        raise ValueError(f"Unrecognized command: {command}")

if __name__ == '__main__':
    main()