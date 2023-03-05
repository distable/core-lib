from pathlib import Path

import numpy as np
from PIL import Image

from src_core.classes.printlib import trace


def pil2cv(img: Image) -> np.ndarray:
    return np.asarray(img)


def cv2pil(img: np.ndarray) -> Image:
    return Image.fromarray(img)


def ensure_extension(path: str | Path, ext):
    path = Path(path)
    if path.suffix != ext:
        path = path.with_suffix(ext)
    return path


def save_png(pil, path, with_async=False):
    if pil is None:
        return

    with trace(f'save_png({Path(path).relative_to(Path.cwd())}, async={with_async}, {pil})'):
        lpath = ensure_extension(path, '.png')
        path = Path(path)

        if with_async:
            save_async(path, pil)
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            pil.save(path, format="PNG")


def save_async(path, pil) -> None:
    if isinstance(path, Path):
        path = path.as_posix()

    # Use threaded lambda to save image
    def write(im) -> None:
        try:
            if isinstance(im, np.ndarray):
                im = cv2pil(im)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            im.save(path, format='PNG')
        except:
            pass

    import threading
    t = threading.Thread(target=write, args=(pil,))
    t.start()


def save_jpg(pil, path, quality=90):
    path = ensure_extension(path, '.jpg')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pil.save(path, format='JPEG', quality=quality)


def save_npy(path, nparray):
    path = ensure_extension(path, '.npy')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path), nparray)


def save_json(data, path):
    import json
    path = Path(path).with_suffix('.json')

    if isinstance(data, dict) or isinstance(data, list):
        # data = json.dumps(data, indent=4, sort_keys=True)
        data = json.dumps(data)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.as_posix(), 'w') as w:
        w.write(data)


def load_json(path, default='required'):
    import json
    is_required = default == 'required'

    path = Path(path).with_suffix('.json')
    if not path.is_file():
        if is_required:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            return default

    try:
        with open(path.as_posix(), 'r') as r:
            return json.load(r)
    except Exception as e:
        if is_required:
            raise e
        else:
            return default


def load_pil(path: Image.Image | Path | str, size=None):
    ret = None

    if isinstance(path, Image.Image): ret = path
    if isinstance(path, Path): ret = Image.open(path.as_posix())
    if isinstance(path, str) and Path(path).is_file(): ret = Image.open(path)
    if isinstance(path, str) and path.startswith('#'): ret = Image.new('RGB', size or (1, 1), color=path)

    if ret is None:
        raise ValueError(f'Unknown type of path: {type(path)}')

    ret = ret.convert('RGB')
    if size is not None:
        ret = ret.resize(size, Image.LANCZOS)

    return ret


def load_pilarr(pil, size=None):
    pil = load_pil(pil, size)
    return np.array(pil.convert('RGB'))
