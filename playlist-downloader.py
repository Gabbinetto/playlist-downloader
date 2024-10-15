from slugify import slugify
from typing import Self
from multiprocessing import Process
import sys
import subprocess
import concurrent.futures
import os
import json
import eyed3
import urllib.request
import getopt


class Playlist:
    def __init__(self, add_metadata: bool = True, m3u: bool = True, threads: int = 10):
        self.videos: list[dict] = []  # type: ignore
        self.name: str
        self.length: int
        self.metadata: bool = add_metadata
        self.make_m3u: bool = m3u
        self.threads: int = threads

        if not os.path.exists("yt-dlp.exe"):
            print("yt-dlp.exe not found. Downloading executable from github.com...")
            request = urllib.request.urlopen(
                "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            )
            with open("yt-dlp.exe", "wb") as f:
                f.write(request.read())

    def __process_video(self, video: dict, index: int, directory: str) -> str:
        print(f"Processing {video['title']}...")
        file_path: str = os.path.join(directory, f"{slugify(video["title"])}.mp3")
        args: list[str] = [
            ".\\yt-dlp.exe",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--output",
            file_path,
            video["url"],
        ]
        subprocess.run(args, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not self.metadata:
            print(f"{video['title']} downloaded.")
            return file_path

        try:
            print("Writing ID3 tags...")
            audiofile: eyed3.mp3.Mp3AudioFile = eyed3.load(file_path)
            audiofile.initTag(version=(2, 3, 0))
            audiofile.tag.title = video.get("title", "Unknown")
            audiofile.tag.artist = video.get("artist", video.get("uploader", "???"))
            audiofile.tag.album = video.get("album", video.get("channel", "???"))
            audiofile.tag.album_artist = video.get(
                "album_artist", video.get("uploader", "???")
            )
            audiofile.tag.composer = video.get("composer")
            audiofile.tag.genre = video.get("genre")
            audiofile.tag.play_count = video.get("view_count")
            audiofile.tag.copyrigth = video.get("copyright")
            audiofile.tag.track_num = index + 1, self.length

            release_date: str = video.get("release_date", "20000101")
            audiofile.tag.release_date = eyed3.core.Date(
                int(release_date[:4]), int(release_date[4:6]), int(release_date[6:8])
            )

            if video["thumbnails"]:
                thumb_response = urllib.request.urlopen(video["thumbnails"][-1]["url"])
                thumbnail = thumb_response.read()
                audiofile.tag.images.set(
                    3, thumbnail, "image/webp", description="cover"
                )

            audiofile.tag.save()
            print("ID3 Tags written.")
        except IOError as e:
            print("Couldn't load mp3", video["title"], f"\n{e}")

        print(f"{video['title']} downloaded.")
        return file_path

    def fetch(self, url: str) -> Self:
        print("Getting playlist data...")
        res: subprocess.CompletedProcess = subprocess.run(
            [
                ".\\yt-dlp.exe",
                "--flat-playlist",
                "-j",
                url,
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
            video: dict = json.loads(vid)
            if video["title"] == "[Deleted video]":
                continue
            self.videos.append(video)

        self.name = slugify(self.videos[0]["playlist_title"])
        self.length = len(self.videos)

        return self

    def download(self) -> Self:
        if not self.length:
            raise Exception("No data has been fetched or playlist is empty.")

        if not os.path.exists(self.name):
            os.mkdir(self.name)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.threads
        ) as executor:
            for i, video in enumerate(self.videos):
                executor.submit(self.__process_video, video, i, self.name)

        return self

    def save_m3u(self) -> Self:
        m3u: M3U = M3U(self.name + ".m3u8")
        for i, video in enumerate(self.videos):
            file_path: str = self.name + "/" + f"{slugify(video["title"])}.mp3"
            m3u.add_track(file_path, i + 1, video["title"])
        m3u.save()

        return self


class M3U:
    def __init__(self, path: str = "") -> None:
        self.path: str = path
        self.content: list[dict] = []

    def add_track(self, song_filename: str, track_num: int, name: str = "") -> None:
        song: dict = {
            "path": song_filename,
            "track_num": track_num,
            "name": name if name != "" else f"Track {track_num}",
        }
        self.content.append(song)
        self.content.sort(key=lambda item: item["track_num"])

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            song: dict
            for song in self.content:
                f.write(f"#EXTINF:-1, {song['name']}\n{song['path']}\n")


if __name__ == "__main__":
    args: list[str] = sys.argv[1:]

    link: str = ""
    metadata: bool = True
    m3u: bool = True
    m3u_only: bool = False
    threads: int = 5

    if "--no-meta" in args:
        args.remove("--no-meta")
        metadata = False
    if "--no-m3u" in args:
        args.remove("--no-m3u")
        m3u = False
    if "--m3u-only" in args:
        args.remove("--m3u-only")
        m3u_only = True
    if "--threads" in args:
        idx: int = args.index("--threads")
        threads = int(args.pop(idx + 1))
        args.remove("--threads")

    if len(args) > 0:
        link = args[0]
    if link == "":
        link = input("Input playlist link: ")

    playlist = Playlist(metadata, m3u, threads)
    playlist.fetch(link)
    if not m3u_only:
        playlist.download()
    if m3u:
        playlist.save_m3u()
