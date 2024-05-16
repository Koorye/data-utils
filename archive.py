import argparse
import os
import os.path as osp
import subprocess


def is_in_any(substring, strings):
    for string in strings:
        if string in substring:
            return True
    return False


def size_to_int(size):
    if size.endswith('G'):
        return int(size[:-1]) * 1024 * 1024 * 1024
    elif size.endswith('M'):
        return int(size[:-1]) * 1024 * 1024
    elif size.endswith('K'):
        return int(size[:-1]) * 1024
    else:
        return int(size)


def get_filename(path):
    path = path.replace('\\', '/')
    if path.endswith('/'):
        path = path[:-1]
    return path.split('/')[-1]


def get_parent_dir(path):
    path = path.replace('\\', '/')
    if path.endswith('/'):
        path = path[:-1]
        
    if '/' not in path:
        return '.'

    return '/'.join(path.split('/')[:-1])


def if_exists(path):
    return osp.exists(path)


class Compressor(object):
    """
    A util to compress and decompress files using tar and pigz.
    If compressed file size exceeds split_size, the file will be split into smaller files.

    Functions:
    1. compress_single: compress a single file or directory
    2. compress_root: list all files or directory in root and compress them
    3. decompress_single: decompress a single file or directory
    4. decompress_root: list all files or directory in root and decompress them
    5. split: split a compressed file into smaller files
    6. merge: merge smaller files into a single compressed file
    """
    
    def __init__(self, root=None, src=None, dst=None, split='2G'):
        """
        Params:
        - root: root directory, if root is not None, compress all files in root
        - src: source file or directory, if root is None, compress this file or directory
        - dst: destination directory
        """
        self.root = root
        self.src = src
        self.dst = dst
        self.split = split
    
    def compress(self):
        """ compress files """
        if self.root is not None:
            self.compress_root()
        else:
            self.compress_single(self.src, self.dst)
    
    def decompress(self):
        """ decompress files """
        if self.root is not None:
            self.decompress_root()
        else:
            self.decompress_single(self.src, self.dst)
    
    def compress_root(self):
        """ compress all files in root """
        filenames = list(sorted(os.listdir(self.root)))
        for filename in filenames:
            src = osp.join(self.root, filename)
            self.compress_single(src, self.dst)
    
    def decompress_root(self):
        """ decompress all files in root """
        filenames = list(sorted(os.listdir(self.root)))
        for filename in filenames:
            src = osp.join(self.root, filename)
            self.decompress_single(src, self.dst)
        
    def compress_single(self, src, dst):
        """ compress a single file or directory """
        if not if_exists(src):
            print(f"File {src} does not exist, stopping.")
            return
        
        if not if_exists(dst):
            print(f"Output directory {dst} does not exist, creating it.")
            os.makedirs(dst)

        print(f"Compressing {src} to {dst} ...")

        # change directory to src
        parent = get_parent_dir(src)
        src = get_filename(src)
        dst = osp.abspath(dst) + '/' + src + '.tar.gz'

        if self._check_pigz():
            subprocess.run(['tar', '--use-compress-program=pigz', '-cvf', dst, src], cwd=parent)
        else:
            subprocess.run(['tar', '-cvf', dst, src], cwd=parent)

        # check file size
        if osp.getsize(dst) > size_to_int(self.split):
            self.split_file(dst)
            
    def decompress_single(self, src, dst):
        """ decompress a single file or directory """
        if not if_exists(src):
            print(f"File {src} does not exist, stopping.")
            return
        
        if not if_exists(dst):
            print(f"Output directory {dst} does not exist, creating it.")
            os.makedirs(dst)
        
        print(f"Decompressing {src} to {dst}...")

        if osp.isdir(src):
            src = self.merge_file(src)

        if self._check_pigz():
            subprocess.run(['tar', '--use-compress-program=pigz', '-xvf', src, '-C', dst])
        else:
            subprocess.run(['tar', '-xvf', src, '-C', dst])
    
    def split_file(self, path):
        """ split a compressed file into smaller files """
        print(f"Splitting {path}...")
        os.makedirs(path + '-split/', exist_ok=True)
        subprocess.run(['split', '-b', self.split, path, path + '-split/'])
        os.remove(path)
    
    def merge_file(self, path):
        """ merge smaller files into a single compressed file """
        if path.endswith('/'):
            path = path[:-1]
        
        merged_path = path.split('-split')[0]
        print(f"Merging {path}...")
        subprocess.run(f'cat {path}/* > {merged_path}', shell=True)
        return merged_path
    
    def _check_pigz(self):
        """ check if pigz is installed """
        try:
            subprocess.run(['pigz', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("pigz is not installed, using tar instead.")
            return False


def main(args):
    compressor = Compressor(args.root, args.src, args.dst, args.split)
    if args.decompress:
        compressor.decompress()
    else:
        compressor.compress()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=str, help='root directory')
    parser.add_argument('--src', type=str, help='source file or directory')
    parser.add_argument('--dst', type=str, help='destination directory')
    parser.add_argument('--split', type=str, default='2G', help='split size')
    parser.add_argument('--decompress', action='store_true', help='decompress mode')
    args = parser.parse_args()
    main(args)
