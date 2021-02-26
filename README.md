# paper-vision
Detect handwriting on images uploaded to Google Drive - catalog your notes and search anytime.

### Some Initial Setup Required
This isn't some service you can simply start using. Instead, this is meant more as a "starter pack" for you to get started with your own implementation that best suits your needs.  

The utility heavily uses the Google Drive API and the Google Cloud Vision API, so you can refer to their quickstart guides to learn more.  

Once you're familiar with that stuff, simply clone the repo, provide the appropriate credentials file and link it to your Google Cloud Project.  

### Usage
Before you can do anything at all with this utility, you need to have some notes on your Google Drive. If you're using your phone camera to take notes, open up the app and use the camera from there instead - that'll make sure the images are in the correct format. Also, it helps if you organize your notebooks into folders so search and recognition become more filtered.

Once you have the notes ready, you can run recognition on the images:
> python quickstart.py r "Folder Name"

This runs recognition on all the supported images in the folder, creates a map of image to the text contained in it, and uploads the data file back to the folder on Drive.

Now you can run search on your data files:
> python quickstart.py s "search query"

This searches for all folders containing the provided keyword.


### Known Issues
This is a work in progress and is meant for you to use as a starter pack and not a complete project on its own. So don't complain if it feels only half-done, because it is. Anyway, here are some more annoyances:

1. It tries to create folders locally but fails if the folder already exists - this one is simple to fix, just delete the folder if one already exists.
2. It doesn't cache recognized text - well it kind of does, but the cached information isn't used, instead the data is fetched again. To fix this, write the code yourself - it shouldn't be too hard.
3.  Creates new data files on your drive folder - Every time you run recognition on a folder, a new data file is created with the same name, so you could end up with lots of duplicates. If you need to run recognition on a previous folder, simply trash the existing data file on drive. Or write the code to do this for you.
4. Accuracy - Handwriting recognition is hard, so try to make sure the images are good quality and well lit, and that your handwriting isn't a total mess. You could write code to improve accuracy yourself, and if you do - great job!
