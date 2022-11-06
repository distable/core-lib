from pathlib import Path
from typing import List

from PIL import Image

from .printlib import printerr


class PipeData:
    """
    This is semantic data to be piped between jobs and plugins, used as output, can be saved, etc.
    """
    def __init__(self, prompt=None, image=None, **kwargs):
        self.__dict__.update(kwargs)
        self.prompt = prompt
        self.image = image
        self.file = ""

    def save(self, path):
        path = Path(path)
        if isinstance(self.image, Image.Image):
            path.parent.mkdir(parents=True, exist_ok=True)
            path = path.with_suffix(".png")
            self.image.save(path)

            # yay
            # from image import DrawImage
            # image = DrawImage.from_file(path.as_posix())
            # image.draw_image()
        else:
            printerr(f"Cannot save {self.image} to {path}")

        self.file = path.as_posix()

    def set_image(self, dat):
        # Image output is moved into the context
        if isinstance(dat, Image.Image):
            self.image = dat
        elif isinstance(dat, list) and isinstance(dat[0], Image.Image):
            printerr("Multiple images in set_image data, using first")
            self.image = dat[0]

    def set_prompt(self, dat):
        # prompt jobs are copied into the context
        if isinstance(dat, str):
            self.prompt = dat

    @classmethod
    def automatic(cls, dat):
        if isinstance(dat, Image.Image):
            return cls(image=dat)
        if isinstance(dat, list) and isinstance(dat[0], Image.Image):
            return cls(image=dat[0])

    @classmethod
    def file(cls, path):
        path = Path(path)
        if path.suffix == ".png":
            return cls(image=Image.open(path))
        else:
            printerr(f"Cannot load {path}")

