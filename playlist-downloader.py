from slugify import slugify
from typing import Self
from multiprocessing import Process
import sys
import subprocess
import os
import json
import eyed3
import urllib.request


class Playlist:
    def __init__(self, add_metadata: bool = True):
        self.videos: list[dict] = []  # type: ignore
        self.name: str
        self.length: int
        self.metadata: bool = add_metadata

    def __process_video(
        self, video: dict, index: int, directory: str
    ) -> None:
        file_path: str = os.path.join(directory, f"{slugify(video["title"])}.mp3")
        args: list[str] = [
                ".\\yt-dlp.exe",
                "--extract-audio",
                "--audio-format", "mp3",
                "--output", file_path,
                video["url"]
            ]
        subprocess.run(
            args
        )
        if not self.metadata:
            return

        try:
            audiofile: eyed3.mp3.Mp3AudioFile = eyed3.load(file_path)
            audiofile.initTag(version=(2, 3, 0))
            audiofile.tag.title = video.get("title", "Unknown")
            audiofile.tag.artist = video.get("artist", video.get("uploader", "???"))
            audiofile.tag.album = video.get("album", video.get("channel", "???"))
            audiofile.tag.album_artist = video.get("album_artist", video.get("uploader", "???"))
            audiofile.tag.composer = video.get("composer")
            audiofile.tag.genre = video.get("genre")
            audiofile.tag.play_count = video.get("view_count")
            audiofile.tag.copyrigth = video.get("copyright")
            audiofile.tag.track_num = index + 1, self.length

            release_date: str = video.get("release_date", "20000101")
            audiofile.tag.release_date = eyed3.core.Date(int(release_date[:4]), int(release_date[4:6]), int(release_date[6:8]))

            if video["thumbnails"]:
                thumb_response = urllib.request.urlopen(video["thumbnails"][-1]["url"])
                thumbnail = thumb_response.read()
                audiofile.tag.images.set(3, thumbnail, "image/webp", description="cover")

            audiofile.tag.save()
            print("ID3 Tags set")
        except IOError as e:
            print("Couldn't load mp3", video["title"], f"\n{e}")


    def fetch(self, url: str) -> Self:
        res: subprocess.CompletedProcess = subprocess.run(
            [
                ".\\yt-dlp.exe",
                "--flat-playlist",
                "-j",
                playlist_link,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
        output: str = res.stdout.strip().split("\n")
        if not len(output) or not any([bool(i) for i in output]):
            raise Exception("Could not fetch playlist or playlist is empty")

        vid: str
        for vid in output:
            self.videos.append(json.loads(vid))

        self.name = slugify(self.videos[0]["playlist_title"])
        self.length = len(self.videos)

        return self

    def download(self) -> Self:
        if not self.length:
            raise Exception("No data has been fetched or playlist is empty.")

        if not os.path.exists(self.name):
            os.mkdir(self.name)

        for i, video in enumerate(self.videos):
            self.__process_video(video, i, self.name)

        return self



if __name__ == "__main__":
    playlist_link: str
    if len(sys.argv) > 1:
        playlist_link = sys.argv[1]
    else:
        playlist_link = input("Link to the playlist: ")
    
    if not playlist_link:
        raise Exception("No link was passed")

    playlist: Playlist = Playlist(add_metadata = not ("--no-metadata" in sys.argv)).fetch(playlist_link).download()
