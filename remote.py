import argparse
import json
import os
import os.path as osp
import paramiko
import subprocess
import stat
import time


def get_filename(path):
    path = path.replace('\\', '/')
    if path.endswith('/'):
        path = path[:-1]
    return path.split('/')[-1]


class Client(object):
    """
    A client to send and receive files using SFTP.
    
    Functions:
    1. send: send a file or directory to remote server
    2. receive: receive a file or directory from remote server
    
    Progress bar should be like this:
    <path> <sent_bytes> / <total bytes> (ratio%) estimate time left: <eta>.
    """
    
    def __init__(self, host, port, username, password):
        """
        Params:
        - host: remote server host
        - port: remote server port
        - username: remote server username
        - password: remote server password
        """
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.host, self.port, self.username, self.password)
        
        # sftp
        self.sftp = self.client.open_sftp()
        
        self.start_time = None
        self.prev_time = None
    
    def send(self, src, dst):
        """ send a file or directory to remote server """
        if not osp.isdir(src):
            dst = osp.join(dst, get_filename(src))
            self.send_file(src, dst)
            return
        
        dst = osp.join(dst, get_filename(src) + '/')
        self.client.exec_command(f'mkdir -p {dst}')

        for root, _, filenames in os.walk(src):
            if not src.endswith('/'):
                src += '/'
            
            dst_root = dst if root == src else osp.join(dst, root[len(src):])
            self._remote_mkdir(dst_root)

            for filename in list(sorted(filenames)):
                local_path = osp.join(root, filename)
                remote_path = osp.join(dst_root, filename)
                self.send_file(local_path, remote_path)
    
    def receive(self, src, dst):
        """ receive a file or directory from remote server """
        if not self._remote_is_dir(src):
            dst = osp.join(dst, get_filename(src))
            self.receive_file(src, dst)
            return
        
        dst = osp.join(dst, get_filename(src) + '/')
        os.makedirs(dst, exist_ok=True)
        
        for root, _, filenames in self._remote_walk(src):
            if not src.endswith('/'):
                src += '/'
            
            dst_root = dst if root == src else osp.join(dst, root[len(src):])
            os.makedirs(dst_root, exist_ok=True)
            
            for filename in list(sorted(filenames)):
                remote_path = osp.join(root, filename)
                local_path = osp.join(dst_root, filename)
                self.receive_file(remote_path, local_path)
    
    def send_file(self, local_path, remote_path):
        """ send a file to remote server """
        self.start_time = time.time()
        self.prev_time = time.time()

        transport = self.client.get_transport()
        transport.set_keepalive(30)
        
        local_md5 = self._md5sum(local_path)
        remote_md5 = self._remote_md5sum(remote_path)
        self.filename = get_filename(local_path)

        while local_md5 != remote_md5:
            if remote_md5 is not None:
                print(f'{self.filename} md5sum not match. Resending...')
                
            self.sftp.put(local_path, remote_path, callback=self._progress)
            remote_md5 = self._remote_md5sum(remote_path)
        
        print(f'{self.filename} sent successfully.')
    
    def receive_file(self, remote_path, local_path):
        """ receive a file from remote server """
        self.start_time = time.time()
        self.prev_time = time.time()
        
        transport = self.client.get_transport()
        transport.set_keepalive(30)
        
        self.filename = get_filename(remote_path)
        self.sftp.get(remote_path, local_path, callback=self._progress)

        remote_md5 = self._remote_md5sum(remote_path)
        local_md5 = self._md5sum(local_path)
        
        while remote_md5 != local_md5:
            print(f'{self.filename} md5sum not match. Resending...')
            self.sftp.get(remote_path, local_path, callback=self._progress)
            local_md5 = self._md5sum(local_path)
        
        print(f'{self.filename} received successfully.')

    def _progress(self, sent, size):
        """ print progress bar """
        cur_time = time.time()
        if cur_time - self.prev_time > 1:
            ratio = sent / size
            speed = sent / (cur_time - self.start_time) / 1024
            eta = (time.time() - self.start_time) * (1 - ratio) / (ratio + 1e-8)
            print(f'{self.filename}: {sent} / {size} ({ratio:.2%}), speed: {speed:.2f} KB/S, estimate time left: {eta:.2f}s.')
            self.prev_time = cur_time
    
    def _md5sum(self, path):
        """ get md5sum of local file """
        result = subprocess.run(['md5sum', path], stdout=subprocess.PIPE)
        return result.stdout.decode().split()[0]
    
    def _remote_mkdir(self, remote_path):
        """ create remote directory """
        try:
            self.sftp.stat(remote_path)
        except:
            self.sftp.mkdir(remote_path)
    
    def _remote_walk(self, remote_path):
        """ walk through remote directory """
        # use sftp.listdir_attr to get file properties
        # return root, dir, file
        
        dirnames, filenames = [], []
        
        outs_ = []
        
        for entry in self.sftp.listdir_attr(remote_path):
            print(entry.filename, entry.st_mode)
            if self._remote_is_dir(osp.join(remote_path, entry.filename)):
                dirnames.append(entry.filename)
                # dir as root
                outs_ += self._remote_walk(osp.join(remote_path, entry.filename))
            else:
                filenames.append(entry.filename)
        
        outs = [(remote_path, dirnames, filenames)] + outs_
        return outs
    
    def _remote_is_dir(self, remote_path):
        """ check if remote path is a directory """
        return stat.S_ISDIR(self.sftp.stat(remote_path).st_mode)
    
    def _remote_md5sum(self, remote_path):
        """ get md5sum of remote file """
        try:
            self.sftp.stat(remote_path)
        except FileNotFoundError:
            return None
            
        _, stdout, _ = self.client.exec_command(f'md5sum {remote_path}')
        return stdout.read().decode().split()[0]


def main(args):
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
        client = Client(config['host'], config['port'], config['username'], config['password'])
    else:
        client = Client(args.host, args.port, args.username, args.password)
    
    if not args.receive:
        client.send(args.src, args.dst)
    else:
        client.receive(args.src, args.dst)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, help='config file')
    parser.add_argument('--host', type=str, help='remote server host')
    parser.add_argument('--port', type=int, help='remote server port')
    parser.add_argument('--username', type=str, help='remote server username')
    parser.add_argument('--password', type=str, help='remote server password')
    parser.add_argument('--src', type=str, help='source file or directory')
    parser.add_argument('--dst', type=str, help='destination file or directory')
    parser.add_argument('--receive', action='store_true', help='receive file from remote server')
    args = parser.parse_args()

    main(args)