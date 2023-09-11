import pytube as pt
import sys
import os
import re
import unicodedata
import eyed3
import urllib.request


def slugify(value, allow_unicode=False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


# playlist = pt.Playlist("https://www.youtube.com/playlist?list=PL7_XL8L2PxkolJPc__sZgkAl0_qLQBc-x")

# # Check if folder exists
# folder = slugify(playlist.title)
# if not os.path.exists(folder):
#     os.mkdir(folder)

# for i, video in enumerate(playlist.videos):
#     file_name = slugify(video.title)
#     stream = video.streams.filter(only_audio=True).first()
#     stream.download(output_path=folder, filename=file_name + ".mp3")

#     audiofile = eyed3.load(os.path.join(os.path.join(folder, file_name + ".mp3")))
#     if audiofile:
#         if not audiofile.tag:
#             audiofile.initTag()

#         audiofile.tag.title = video.title
#         audiofile.tag.artist = video.author
#         audiofile.tag.album = playlist.title
#         audiofile.tag.album_artist = playlist.owner
#         audiofile.tag.track_num = (i + 1, playlist.length)

#         thumbnail = urllib.request.urlopen(video.thumbnail_url)
#         imagedata = thumbnail.read()
#         audiofile.tag.images.set(3, imagedata, "image/jpeg", "cover")

#         audiofile.tag.save()


class PlaylistDownloader:
    def __init__(self, url: str, metadata=True) -> None:
        """Download a Youtube playlist as music files

        Args:
            url (str): The playlist url.
            metadata (bool, optional): Add ID3 metadata tags. Defaults to True.
        """

        self.playlist = pt.Playlist(url)
        self.metadata = metadata

    def download(self, output_folder: str = "", print_progress: bool = True):
        """Download the entire playlist as .mp3 files

        Args:
            output_folder (str, optional): The output folder. Defaults to a slugified version of the playlist's title.
        """
        if output_folder == "":
            output_folder = slugify(self.playlist.title)

        if not os.path.exists(output_folder):
            os.mkdir(output_folder)

        for i, video in enumerate(self.playlist.videos):
            file_name = slugify(video.title)
            stream = video.streams.filter(only_audio=True).first()
            stream.download(output_path=output_folder, filename=file_name + ".mp3")

            if self.metadata:
                self.__add_tags(
                    os.path.join(output_folder, file_name + ".mp3"), video, i + 1
                )

            print("Downloaded: ", video.title)

    def __add_tags(self, file_path: str, video: pt.YouTube, index: int = None):
        audiofile = eyed3.load(file_path)

        if audiofile:
            if not audiofile.tag:
                audiofile.initTag()

            audiofile.tag.title = video.title
            audiofile.tag.artist = video.author
            audiofile.tag.album = self.playlist.title
            audiofile.tag.album_artist = self.playlist.owner
            if index != None:
                audiofile.tag.track_num = (index, self.playlist.length)

            thumbnail = urllib.request.urlopen(video.thumbnail_url)
            imagedata = thumbnail.read()
            audiofile.tag.images.set(3, imagedata, "image/jpeg", "cover")

            audiofile.tag.save()


if __name__ == "__main__":
    url = input("Insert playlist url: ")
    metadata = True
    if input("Add metadata tags? (Leave blank for yes, type anything for no): ") != "":
        metadata = False

    playlist = PlaylistDownloader(url, metadata)
    playlist.download()
    print("Done.")
