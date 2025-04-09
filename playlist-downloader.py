from typing import Self, Any
from slugify import slugify
from mutagen.id3 import (
    TIT2,
    COMM,
    TOPE,
    TPE1,
    APIC,
    TRCK,
    TCOM,
    TCON,
    TOAL,
    TDAT,
    SYLT,
    USLT,
)
from mutagen.mp3 import MP3
import yt_dlp as yt
import json, os, getopt, sys
import urllib.request
import syncedlyrics as sl


OUTPUT_PATH: str = "output"
LOG_FILE: str = "playlist.log"


# Taken from the GitHub
class Logger:

    def __init__(self):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("LOG START\n")

    def debug(self, msg: str):
        if msg.startswith("[debug] "):
            pass
        else:
            self.info(msg)

    def info(self, msg: str):
        with open(LOG_FILE, "w+", encoding="utf-8") as f:
            f.write(msg)

    def warning(self, msg: str):
        print(msg)
        with open(LOG_FILE, "w+", encoding="utf-8") as f:
            f.write(msg)

    def error(self, msg: str):
        print(msg)
        with open(LOG_FILE, "w+", encoding="utf-8") as f:
            f.write(msg)


class PlaylistDownloader:

    def __init__(
        self,
        playlist_url: str,
        json_info_file: str = None,
        add_metadata: bool = True,
        add_lyrics: bool = True,
    ):

        self.url = playlist_url
        self.raw_info: dict[str, Any] = {}
        self.info: dict[str, Any] = {}
        self.output_folder: str = ""
        self.metadata = add_metadata
        self.lyrics = add_lyrics
        self.logger = Logger()

        self.options = {
            "quiet": True,
            "logger": self.logger,
            "progress_hooks": [self.__hook],
            "format": "mp3/bestaudio/best",
            "postprocessors": [
                {  # Extract audio using ffmpeg
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }
            ],
        }

        if json_info_file != None:
            with open(json_info_file, "r", encoding="utf-8") as f:
                self.raw_info = json.load(f)

    def __hook(self, d: dict) -> None:
        if d["status"] == "finished":
            print("Done downloading, now post-processing...")

    def fetch_info(self, cache_info: bool = False) -> Self:

        with yt.YoutubeDL() as ydl:
            self.raw_info = ydl.extract_info(self.url, download=False)

        if cache_info:
            with open("last_raw_fetch.json", "w", encoding="utf-8") as f:
                json.dump(self.raw_info, f, indent=2)

        return self

    def process_info(self) -> Self:

        self.info["title"] = self.raw_info.get("title", "No title")
        self.info["slug"] = slugify(self.info["title"])
        self.output_folder = os.path.join(OUTPUT_PATH, self.info["slug"])
        os.makedirs(self.output_folder, exist_ok=True)

        entries: list[dict[str, Any]] = self.raw_info.get("entries", [])

        self.info["count"] = len(entries)
        self.info["songs"] = []

        for entry in entries:
            self.info["songs"].append(self.__process_entry(entry))

        return self

    def __process_entry(self, entry: dict) -> dict[str, Any]:
        data: dict = {
            "title": entry.get("title", "No song title"),
            "url": entry.get("original_url", ""),
            "comment": entry.get("description", ""),
            "artists": entry.get("artists", [entry.get("channel", "")]),
            "index": entry.get("playlist_index", 0),
            "album": entry.get("album", ""),
            "genres": entry.get("genres", []),
            "composers": entry.get("composers", []),
        }

        data["slug"] = slugify(data["title"])
        data["filename"] = data["slug"] + ".mp3"
        data["path"] = os.path.join(self.output_folder, data["filename"])
        data["final_path"] = os.path.join(self.info["slug"], data["filename"])

        date: str = entry.get("release_date", "")
        if date:
            data["date"] = date[-2:] + date[-4:-2]

        thumbnails: list[dict[str, Any]] = entry.get("thumbnails", [])
        for thumbnail in thumbnails[::-1]:
            width, height = thumbnail.get("width", -1), thumbnail.get("height", -1)
            if width != -1 and width == height:
                data["thumbnail"] = thumbnail.get("url", "")
                data["thumbnail_mime"] = "image/jpeg"
                break
        if not data.get("thumbnail"):
            data["thumbnail"] = entry.get("thumbnail", "")
            data["thumbnail_mime"] = "image/webp"

        return data

    def download(self) -> Self:

        for song in self.info["songs"]:
            print(f"Downloading {song['title']}...")
            self.__download_song(song)
            print("Done.\n")

        return self

    def __download_song(self, song: dict[str, Any]) -> None:
        options = dict(self.options)
        options["outtmpl"] = {"default": song["path"][:-4]}

        with yt.YoutubeDL(options) as ytd:
            try:
                ytd.download([song["url"]])
                if self.metadata:
                    print("Adding metadata...")
                    self.__add_metadata(song["path"], song)
            except yt.utils.DownloadError as e:
                print("Couldn't download", song["title"], "\b:", e)

    def __add_metadata(self, path: str, song: dict[str, Any]) -> None:
        audiofile: MP3 = MP3(path)
        if not audiofile.tags:
            audiofile.add_tags()

        audiofile.tags.add(TIT2(text=[song["title"]]))
        audiofile.tags.add(COMM(text=[song["comment"]]))
        audiofile.tags.add(TOAL(text=[song["album"]]))
        if song.get("date"):
            audiofile.tags.add(TDAT(text=[song["date"]]))
        if song["artists"]:
            audiofile.tags.add(TOPE(text=["/".join(song["artists"])]))
            audiofile.tags.add(TPE1(text=[song["artists"][0]]))
        audiofile.tags.add(TRCK(text=[f"{song['index']}/{self.info['count']}"]))
        if song["composers"]:
            audiofile.tags.add(TCOM(text=["/".join(song["composers"])]))
        if song["genres"]:
            genre_frame = TCON()
            genre_frame.genres = song["genres"]
            audiofile.tags.add(genre_frame)

        # Thumbnail
        if song.get("thumbnail"):
            request = urllib.request.urlopen(song["thumbnail"])
            data = request.read()
            print("Read thumbnail")
            frame = APIC(
                mime=song["thumbnail_mime"],
                type=3,
                desc="cover",
                data=data,
            )
            audiofile.tags.add(frame)

        if self.lyrics:
            self.__add_lyrics(audiofile, song["title"], song["artists"][0])

        audiofile.save()

    def __add_lyrics(self, audiofile: MP3, name: str, artist: str) -> None:
        print("Trying to add lyrics for", name)

        lyrics = sl.search(f"[{name}] [{artist}]", synced_only=True)
        if not lyrics:
            lyrics = sl.search(f"[{name}] [{artist}]", plain_only=True)

        if lyrics:
            print("Lyrics found")

        if not lyrics:
            print("No lyrics found for", name)
            return

        audiofile.tags.add(
            USLT(
                text=lyrics,
            )
        )

        print(f"Added lyrics for", name)

    def make_m3u8(self) -> Self:
        with open(
            os.path.join(self.output_folder, self.info["slug"] + ".m3u8"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:{self.info['title']}\n")
            for song in self.info["songs"]:
                f.write(f"#EXTINF:-1, {song['title']}\n{song['filename']}\n")


def main():
    url: str = ""
    long: str = [
        "help",
        "cache-raw",
        "no-meta",
        "m3u8-only",
        "no-lyrics",
        "json-raw=",
        "url=",
    ]
    options: str = "hcnmlj:u:"

    try:

        arguments, values = getopt.getopt(sys.argv[1:], options, long)

        json_info_file: str = None
        add_metadata: bool = True
        cache_raw: bool = False
        m3u_only: bool = False
        lyrics: bool = True

        for argument, value in arguments:
            if argument in ("-h", "--help"):
                print(
                    """
    Options:
        -h, --help:                                 Show this text.
        -c, --cache-raw:                            Save the raw playlist info file in a JSON (raw_info.json).
        -n, --no-meta:                              Don't add metadata, such as song title and cover image.
        -m, --m3u8-only:                            Only generate the m3u8 file.
        -l, --no-lyrics:                            Won't try to add lyrics through syncedlyrics.
        -j <FILE_PATH>, --json-raw=<FILE_PATH>      Instead of fetching the playlist JSON data, use a cached file, such as one cached with -c.
        -u <PLAYLIST_URL>, --url=<PLAYLIST_URL>     The playlist url. If not set, it will be asked when the script is ran, unless a raw json is passed with -j.
                    """
                )
                return
            if argument in ("-c", "--cache-raw"):
                cache_raw = True
            if argument in ("-n", "--no-meta"):
                add_metadata = False
            if argument in ("-m", "--m3u8-only"):
                m3u_only = True
            if argument in ("-l", "--no-lyrics"):
                lyrics = False
            if argument in ("-j", "--json-raw"):
                json_info_file = value
            if argument in ("-u", "--url"):
                url = value

        if not url and not json_info_file:
            url = input("YouTube Music playlist url: ")

        playlist = PlaylistDownloader(url, json_info_file, add_metadata, lyrics)
        if not json_info_file:
            playlist.fetch_info(cache_raw)
        playlist.process_info()
        if not m3u_only:
            playlist.download()
        playlist.make_m3u8()

    except getopt.error as e:
        print(e)


if __name__ == "__main__":
    main()
