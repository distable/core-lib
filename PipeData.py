from pathlib import Path
from typing import List

from PIL import Image

from .convert import save_png
from .printlib import printerr


class PipeData:
    """
    This is semantic data to be piped between jobs and plugins, used as output, can be saved, etc.
    """

    def __init__(self, prompt=None, image=None, **kwargs):
        self.__dict__.update(kwargs)
        self.prompt = prompt
        self.width:int|None = None
        self.height:int|None = None
        self.image: None|Image  = image
        self.file = ""  # File relative to the session workdir
        self.fps = 24

    @property
    def w(self):
        return self.width

    @w.setter
    def w(self, value):
        self.width = value

    @property
    def h(self):
        return self.height

    @h.setter
    def h(self, value):
        self.height = value

    def save(self, path):
        path = Path(path)
        if isinstance(self.image, Image.Image):
            path = path.with_suffix(".png")
            save_png(self.image, path, with_async=True)

            # yay
            # from image import DrawImage
            # image = DrawImage.from_file(path.as_posix())
            # image.draw_image()
        else:
            printerr(f"Cannot save {self.image} to {path}")

        self.file = path

        return self

    def apply(self, other):
        if other.prompt: self.prompt = other.prompt
        if other.image: self.image = other.image
        if other.file: self.file = other.file
        if other.width: self.width = other.width
        if other.height: self.height = other.height

        # Set width and height from image if not set
        if self.image and not self.width: self.width = self.image.width
        if self.image and not self.height: self.height = self.image.height

        # Resize image to match context size
        if self.image and (self.width != self.image.width or self.height != self.image.height):
            self.image = self.image.resize((self.width, self.height), Image.BICUBIC)

        return self


    def load(self, root):
        if not self.file: return
        root = Path(root)
        file = root / self.file

        if self.file.endswith(".png"):
            if file.exists():
                self.set(file)

        return self

    def set(self, dat):
        from PIL import ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True

        # Image output is moved into the context
        if isinstance(dat, Image.Image):
            self.image = dat
        elif isinstance(dat, str) or isinstance(dat, Path):
            self.image = Image.open(dat)
            self.file = dat
        elif isinstance(dat, list) and isinstance(dat[0], Image.Image):
            printerr("Multiple images in set_image data, using first")
            self.image = dat[0]

        if self.image:
            self.width = self.image.width
            self.height = self.image.height
            self.image = self.image.convert("RGB")

        return self

    def set_prompt(self, dat):
        # prompt jobs are copied into the context
        if isinstance(dat, str):
            self.prompt = dat

        return self

    @classmethod
    def automatic(cls, dat):
        if isinstance(dat, Image.Image):
            return cls(image=dat)
        if isinstance(dat, list) and isinstance(dat[0], Image.Image):
            return cls(image=dat[0])
        else:
            return cls()

    @classmethod
    def file(cls, path):
        path = Path(path)
        return cls().set(path)
