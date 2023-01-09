import math
import os
import pathlib
import shutil
import subprocess
import time
from datetime import datetime
from glob import glob
from pathlib import Path

import PIL
from PIL.Image import Image
from tqdm import tqdm

from . import paths
from .JobInfo import JobInfo
from .PipeData import PipeData
from .paths import get_leadnum_zpad, get_max_leadnum, get_min_leadnum, get_next_leadnum, is_leadnum_zpadded, leadnum_zpad, parse_frames, sessions
from .convert import load_pil
from .logs import logsession, logsession_err
from .printlib import trace


class Session:
    """
    A kind of wrapper for a directory with number sequence padded with 8 zeroes, and
    optionally some saved metadata.

    00000001.png
    00000002.png
    00000003.png
    ...
    00000020.png
    00000021.png
    00000022.png
    """
    def __init__(self, name_or_abspath, load=True, fixpad=False):
        self.ctx = PipeData()
        self.jobs = []
        self.args = dict()
        self.f = 1

        if Path(name_or_abspath).is_absolute():
            self.dirpath = Path(name_or_abspath)
            self.name = Path(name_or_abspath).stem
        elif name_or_abspath is not None:
            self.name = name_or_abspath
            self.dirpath = paths.sessions / name_or_abspath
        else:
            self.valid = False
            logsession_err("Cannot create session! No name or path given!")
            return

        if self.dirpath.exists():
            if load:
                self.try_load()
        else:
            logsession("New session:", self.name)

        if fixpad:
            if self.dirpath.is_dir() and not is_leadnum_zpadded(self.dirpath):
                logsession("Session directory is not zero-padded. Migrating...")
                self.zpad(leadnum_zpad)


    @staticmethod
    def now(prefix=''):
        """
        Returns: A new session which is timestamped to now
        """
        name = datetime.now().strftime(paths.session_timestamp_format)
        if None is None:
            num = get_next_leadnum(directory=sessions)
        return Session(f"{prefix}{name}")

    @staticmethod
    def recent_or_now(recent_window=math.inf):
        """
        Returns: The most recent session, or a new session if none exists.
        args:
            recent_window: The number of seconds to consider a session recent. Outside of this window, a new session is created.
        """
        if any(paths.sessions.iterdir()):
            latest = max(paths.sessions.iterdir(), key=lambda p: p.stat().st_mtime)
            # If the latest session fits into the recent window, use it
            if (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() < recent_window:
                return Session(latest)

        return Session.now()

    # @staticmethod
    # def recent_or_now():
    #     """
    #     Returns: The most recent session, or a new session if none exists
    #     """
    #     else:
    #         return Session.now()

    def try_load(self):
        if self.dirpath.exists():
            if any(self.dirpath.iterdir()):
                recent = None

                # Set the context to the most recent file in the session directory
                with trace('try_load.ordering'):
                    files = self.dirpath.glob('*')
                    l = sum([len(files) for (root, dirs, files) in os.walk(self.dirpath)])

                # Going down in a loop
                # l = len(files)
                now = self.get_frame_path(l)
                while not now.exists() and l > 0:
                    l -= 1
                    now = self.get_frame_path(l)
                if now.exists():
                    recent = now

                if recent is not None:
                    recent = self.dirpath / recent
                    self.ctx = PipeData.file(recent)

                logsession(f"Loaded session {self.name} ({self.ctx.width}x{self.ctx.height}) at {self.dirpath} ({self.ctx.file})")
            else:
                logsession(f"Loaded session {self.name} at {self.dirpath}")

            # TODO load a session metadata file
            self.seek_max(prints=False)

    def last_prop(self, propname: str):
        for arglist in self.args:
            for k, v in arglist:
                if k == propname:
                    return v

        return None

    @property
    def nice_path(self):
        # If is relative to the sessions folder, return the relative path
        if self.dirpath.is_relative_to(paths.sessions):
            return self.dirpath.relative_to(paths.sessions)
        else:
            return self.dirpath.resolve()


    @property
    def last_frame_path(self):
        return self.get_frame_path(get_max_leadnum(self.dirpath))

    @property
    def first_frame_path(self):
        return self.get_frame_path(get_min_leadnum(self.dirpath))

    @property
    def f_first(self):
        return get_min_leadnum(self.dirpath)

    @property
    def f_last(self):
        return get_max_leadnum(self.dirpath)

    @property
    def t(self):
        return self.f / self.ctx.fps

    @property
    def w(self):
        return self.ctx.width

    @property
    def h(self):
        return self.ctx.height

    def get_frame_path(self, f, subdir=''):
        p1 = (self.dirpath / subdir / str(f)).with_suffix('.png')
        p2 = (self.dirpath / subdir / str(f).zfill(8)).with_suffix('.png')
        if p1.exists(): return p1
        return p2  # padded is now the default

    def current_frame_path(self, subdir=''):
        return self.get_frame_path(self.f, subdir)

    def current_frame_exists(self):
        return self.current_frame_path().is_file()

    def save(self, dat: PipeData = None, path=None):
        dat = dat or self.ctx
        path = path or self.ctx.file

        if not Path(path).is_absolute():
            path = self.dirpath / path

        dat.save(path)

    def save_add(self, subdir='', dat: PipeData = None):
        dat = dat or self.ctx

        # Append to the current frame
        path = self.dirpath / subdir / str(self.f)

        dat.save(path)

        # Update the context file path
        p = self.dirpath / (dat.file or '1.png')
        p = p.with_name(str(self.f)).with_suffix('.png')
        p = p.relative_to(self.dirpath)
        dat.file = str(p)
        self.f += 1

    def add_job(self, j):
        self.jobs.append(j)

    def rem_job(self, j):
        self.jobs.remove(j)

    def add_kwargs(self, ifo: JobInfo, kwargs):
        key = ifo.get_groupclass()
        if key in self.args:
            self.args[key].update(kwargs)
        else:
            self.args[key] = {**kwargs}

    def get_kwargs(self, ifo: JobInfo):
        key = ifo.get_groupclass()
        if key in self.args:
            return self.args[key]
        else:
            return {}


    def seek(self, i=None, prints=True):
        if i is None:
            # Seek to next
            self.f = get_next_leadnum(self.dirpath)
            self.ctx.file = f'{str(self.f)}.png'
            self.ctx.load(self.dirpath)
            if print: logsession("Seek to", self.f)
        elif isinstance(i, int):
            # Seek to i
            i = max(i, 1)  # Frames start a 1
            self.f = i
            self.ctx.file = f'{str(i)}.png'
            self.ctx.load(self.dirpath)
            if print: logsession("Seek to", self.f)
        else:
            logsession_err(f"Invalid seek argument: {i}")

    def seek_min(self, prints=True):
        if any(self.dirpath.iterdir()):
            # Seek to next
            self.f = get_min_leadnum(self.dirpath)
            self.seek(self.f, prints)

    def seek_max(self, prints=True):
        if any(self.dirpath.iterdir()):
            self.f = get_max_leadnum(self.dirpath)
            self.seek(self.f, prints)

    def seek_next(self, i=1):
        self.f += i
        self.seek(self.f)


    @property
    def image(self):
        return self.ctx.image

    def subsession(self, name):
        if name:
            return Session(self.res(name))
        else:
            return self

    def res(self, subpath: Path | str) -> Path:
        """
        Get a session resource, e.g. init video
        """
        subpath = Path(subpath)
        if subpath.is_absolute():
            return subpath

        return self.dirpath / subpath

    def res_frame(self, resid, subdir='', ext=None, loop=False) -> Path | None:
        """
        Get a session resource, and automatically fetch a frame from it.
        Usage:

        resid='video.mp4:123' # Get frame 123 from video.mp4
        resid='video:3' # Get frame 3 from video.mp4
        resid='video' # Get the current session frame from video.mp4
        resid=3 # Get frame 3 from the current session
        """

        # If the resid is a number, assume it is a frame number
        if isinstance(resid, int):
            return self.res(f'{resid}.png')
        elif resid is None:
            return self.res(f'{self.f}.png')

        # If the resid is a string, parse it
        nameparts = resid.split(':')
        file = Path(nameparts[0])  # The name of the resource with or without extension
        stem = Path(file.stem)  # The name of the resource with or without extension
        frame = self.f
        if len(nameparts) > 1:
            frame = int(nameparts[-1])

        # File exists and is not a video --> return directly / same behavior as res(...)
        if stem.is_file():
            if not stem.suffix in paths.video_exts:
                return stem

        # Iterate dir and find the matching file, regardless of the extension
        framedir = self.res(stem / subdir)
        # if not framedir.is_dir():
        #     self.extract_frames()

        l = list(framedir.iterdir())
        if loop:
            frame = frame % len(l)

        framestr = str(frame)
        for file in l:
            if file.stem.lstrip('0') == framestr:
                if ext is None or file.suffix.lstrip('.') == ext.lstrip('.'):
                    return file

        return None

    def res_framepil(self, name, subdir='', ext=None, loop=False, ctxsize=False) -> Path | None:
        ret = load_pil(self.res_frame(name, subdir, ext, loop))
        if ctxsize:
            ret = ret.resize((self.ctx.width, self.ctx.height))

        return ret


    def extract_frames(self, vidpath, nth_frame=1, frame_range: tuple | None = None, force=False) -> Path | str | None:
        vidpath = self.res(vidpath)

        vf = f'select=not(mod(n\\,{nth_frame}))'
        if frame_range is not None:
            vf += f',select=between(t\\,{frame_range[0]}\\,{frame_range[1]})'

        if vidpath.exists():
            output_path = self.res(vidpath.with_suffix(''))

            if output_path.exists():
                if not force:
                    logsession(f"Frame extraction already exists for {vidpath.name}, skipping ...")
                    return output_path
                else:
                    logsession(f"Frame extraction already exists for {vidpath.name}, overwriting ...")
                    import shutil
                    shutil.rmtree(output_path)

            output_path.mkdir(parents=True, exist_ok=True)

            # TODO wtf is this for?
            print(f"Exporting Video Frames (1 every {nth_frame})...")
            try:
                for f in [o.replace('\\', '/') for o in glob(f'{output_path}/*.png')]:
                    # for f in pathlib.Path(f'{output_path}').glob('*.png'):
                    pathlib.Path(f).unlink()
            except:
                print('error deleting frame ', f)

            try:
                subprocess.run(['ffmpeg', '-i', f'{vidpath}', '-vf', f'{vf}', '-vsync', 'vfr', '-q:v', '2', '-loglevel', 'error', '-stats', f'{output_path}/%06d.png'], stdout=subprocess.PIPE).stdout.decode('utf-8')
            except:
                subprocess.run(['ffmpeg.exe', '-i', f'{vidpath}', '-vf', f'{vf}', '-vsync', 'vfr', '-q:v', '2', '-loglevel', 'error', '-stats', f'{output_path}/%06d.png'], stdout=subprocess.PIPE).stdout.decode('utf-8')

            return output_path
        else:
            return None


        # def run(self, query: JobArgs | str | None = None, **kwargs):
        #     """
        #     Run a job in the current session context, meaning the output JobState data will be saved to disk
        #     """
        #     ret = plugins.run(query, print=logsession, **kwargs)
        #     current.save_next(ret)
        #     print("")

    def make_video(self, fps, skip=3, bg=False, music='', music_start=0, frames=None, fade_in=.5, fade_out=1.25, upscale_w=None, upscale_h=None):
        # call ffmpeg to create video from image sequence in session folder
        # do not halt, run in background as a new system process

        # Detect how many leading zeroes are in the frame files
        lzeroes = get_leadnum_zpad(self.dirpath)

        pattern_with_zeroes = '%d.png'
        if lzeroes >= 2:
            pattern_with_zeroes = f'%0{lzeroes}d.png'

        musicargs = []
        if music:
            musicargs = ['-ss', str(music_start), '-i', music]

        name = 'video'
        vf = ''

        def add_vf(s):
            nonlocal vf
            if vf:
                vf += ','
            vf += s

        # Frame range
        # ----------------------------------------
        frameargs1 = ['-start_number', str(max(skip, self.f_first + skip))]
        frameargs2 = []
        if frames is not None:
            name, lo, hi = self.parse_frames(name, frames)
            print(f'Frame range: {lo} : {hi}')
            frameargs1 = ['-start_number', str(lo)]
            frameargs2 = ['-frames:v', str(hi - lo + 1)]

        # Determine framecount from filename pattern
        framecount = self.f
        duration = framecount / fps

        # VF filters
        # ----------------------------------------
        if fade_in < duration:
            add_vf(f'fade=in:st=0:d={fade_in}')
        if fade_out < duration:
            add_vf(f'fade=out:st={self.f / fps - fade_out}:d={fade_out}')

        # Upscale
        # ----------------------------------------
        if upscale_w is not None:
            ratio = upscale_w / self.ctx.width
            upscale_h = int(self.ctx.height * ratio)
            add_vf(f'scale={upscale_w}:{upscale_h}')
            print(f"Making video at {upscale_w}x{upscale_h}")
        if upscale_h is not None:
            ratio = upscale_h / self.ctx.height
            upscale_w = int(self.ctx.width * ratio)
            add_vf(f'scale={upscale_w}:{upscale_h}')
            print(f"Making video at {upscale_w}x{upscale_h}")
        if upscale_w is None and upscale_h is None:
            print(f"Making video at {self.ctx.width}x{self.ctx.height}")
        print('vf: ', vf)

        # Run
        # ----------------------------------------
        out = self.dirpath / f'{name}.mp4'
        pattern = self.dirpath / pattern_with_zeroes
        args = ['ffmpeg', '-y', '-r', str(fps), *frameargs1, '-i', pattern.as_posix(), *frameargs2, '-vf', vf, *musicargs, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', out.as_posix(), '-nostats']

        print('')
        print(' '.join(args))

        # Don't print output to console
        if bg:
            subprocess.Popen(args)
        else:
            subprocess.run(args)

        return out


    def make_rife(self, frames=None):
        RESOLUTION = 2  # How much interpolation (2 == twice as many frames)

        name = 'rife'
        lo = None
        hi = None
        if frames:
            name, lo, hi = self.parse_frames(name, frames)

        input = self.dirpath
        tmp = self.res('rife_tmp')
        output = self.dirpath / name

        lead = get_max_leadnum(input)
        lo = lo or 0
        hi = hi or lead

        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(output, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)

        print(f"make_rife(input={input}, output={output}, lo={lo}, hi={hi if hi < lead else 'max'})")

        # Copy  %d.png frames to tmp folder
        # ----------------------------------------
        lead = hi - lo
        tq = tqdm(total=lead)
        tq.set_description(f"Copying frames to {tmp.relative_to(self.dirpath)} ...")
        lz = max(len(str(lo)), len(str(hi)))

        for f in input.iterdir():
            if f.is_file():
                try:
                    leadnum = int(f.stem)
                except:
                    leadnum = -1

                if lo <= leadnum <= hi:
                    shutil.copy(f, tmp / f"{leadnum:0{lz}d}.png")
                    tq.update(1)

        # Finish the tq
        tq.update(lead - tq.n)
        tq.close()

        # Run RIFE with tqdm progress bar
        # ----------------------------------------
        args = ['rife-ncnn-vulkan', '-i', tmp.as_posix(), '-o', output.as_posix()]
        print(' '.join(args))

        lead = (hi - lo) * 2
        start_num = len(list(output.iterdir()))
        end_num = start_num + lead

        tq = tqdm(total=lead)
        tq.set_description(f"Running rife ...")
        last_num = start_num

        proc = subprocess.Popen(args)
        while proc.poll() is None:
            cur_num = len(list(output.iterdir()))
            diff = cur_num - last_num
            if diff > 0:
                tq.update(diff)
                last_num = cur_num

            tq.refresh()
            time.sleep(1)

        shutil.rmtree(tmp)
        tq.update(lead - tq.n)
        tq.close()

        # Rename RIFE outputs to add with lo
        # ----------------------------------------
        for f in output.iterdir():
            if f.is_file():
                try:
                    leadnum = int(f.stem)
                except:
                    leadnum = -1

                if leadnum >= 0:
                    newname = f"{leadnum + lo * RESOLUTION - 1}.png"
                    f.rename(output / newname)

        return output

    def zpad(self, zeroes=8):
        """
        Pad the frame numbers with 8 zeroes
        """
        for f in self.dirpath.iterdir():
            if f.is_file():
                try:
                    num = int(f.stem)
                    newname = f"{num:0{zeroes}d}.png"
                    f.rename(f.with_name(newname))
                except:
                    pass

    def unpad(self):
        """
        Remove leading zeroes from frame numbers
        """
        for f in self.dirpath.iterdir():
            if f.is_file():
                try:
                    num = int(f.stem)
                    newname = f"{num}.png"
                    f.rename(f.with_name(newname))
                except:
                    pass

    def parse_frames(self, name, frames):
        name, lo, hi = parse_frames(name, frames)
        if lo is None: lo = self.f_first
        if hi is None: hi = self.f_last
        return name, lo, hi
