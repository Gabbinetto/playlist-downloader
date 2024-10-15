Python class to download a YouTube playlist as .mp3 files. Requires [yt-dlp](https://github.com/yt-dlp/yt-dlp) executable to be in the same folder. If the executable isn't found, it will be downloaded from the official repository.

## Using
The program will create a folder with the same name of the playlist, but slugified. Then all the songs will be downloaded in that same folder as `<slugified-song-name>.mp3`. Finally, a `.m3u8` playlist file will be created as a sibling to the folder. This file must be a sibling to the playlist folder to work.

Run `playlist-downloader.py`. If no link is passed as argument, it will be asked.

Valid arguments:
- **--no-meta**: won't add ID3 metadata to the `.mp3` files
- **--no-m3u**: won't generate the `.m3u8` file
- **--m3u-only**: will only generate the `.m3u8` file
- **--threads**: number of threads to use, followed by the number of threads (Default: 10)

### Example
If the user wants to download a playlist called "Cool playlist" that contains these songs:
- Cool song 1
- Cool song 2
- Very cool song

After running `playlist-downloader.py` with only the playlist link as an argument, the folder containing the program will look like this:
```
playlist-downloader.py
yt-dlp.exe
cool-playlist.m3u8
cool-playlist/
-- cool-song-1.mp3
-- cool-song-2.mp3
-- very-cool-song.mp3
```