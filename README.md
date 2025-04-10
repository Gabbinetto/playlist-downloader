Python class to download a YouTube playlist as .mp3 files.

## Usage

The program will create a folder with the same name of the playlist, but slugified. Then all the songs will be downloaded in that same folder as `<slugified-song-name>.mp3`. Finally, a `.m3u8` playlist file will be created. This file must be inside of the playlist folder to work.

Run `playlist-downloader.py`.

```
Options:
    -h, --help:                                 Show this text.
    -c, --cache-raw:                            Save the raw playlist info file in a JSON (raw_info.json).
    -n, --no-meta:                              Don't add metadata, such as song title and cover image.
    -m, --m3u8-only:                            Only generate the m3u8 file.
    -l, --no-lyrics:                            Won't try to add lyrics through syncedlyrics.
    -d, --difference:                           Download only the difference based on the existing .m3u8 file in the target directory.
    -j <FILE_PATH>, --json-raw=<FILE_PATH>      Instead of fetching the playlist JSON data, use a cached file, such as one cached with -c.
    -u <PLAYLIST_URL>, --url=<PLAYLIST_URL>     The playlist url. If not set, it will be asked when the script is ran, unless a raw json is passed with -j.
```

### Example

If the user wants to download a playlist called "Cool playlist" that contains these songs:

- Cool song 1
- Cool song 2
- Very cool song

After running `playlist-downloader.py` with only the playlist link as an argument, the folder containing the program will look like this:

```
playlist-downloader.py
output/
-- cool-playlist/
-- -- cool-playlist.m3u8
-- -- cool-song-1.mp3
-- -- cool-song-2.mp3
-- -- very-cool-song.mp3
```
