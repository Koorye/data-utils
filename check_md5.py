import argparse
import os
import os.path as osp
import paramiko
import subprocess
import threading


def md5sum(file_path):
    """ calculate md5sum of a file """
    result = subprocess.run(['md5sum', file_path], stdout=subprocess.PIPE)
    return result.stdout.decode().split()[0]


def remote_md5sum(client, remote_path):
    """ get md5sum of a remote file """
    _, stdout, _ = client.exec_command(f'md5sum {remote_path}')
    return stdout.read().decode().split()[0]


class CheckMD5Thread(threading.Thread):
    def __init__(self, client, local_path, remote_path):
        super(CheckMD5Thread, self).__init__()
        self.client = client
        self.local_path = local_path
        self.remote_path = remote_path
        self.local_md5 = None
        self.remote_md5 = None

    def run(self):
        self.local_md5 = md5sum(self.local_path)
        self.remote_md5 = remote_md5sum(self.client, self.remote_path)
        if self.local_md5 == self.remote_md5:
            print(f'{self.local_path} is the same as {self.remote_path}')
        else:
            print(f'{self.local_path} is different from {self.remote_path}')
            

def main(args):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, args.port, args.username, args.password)

    threads = []
    for root, _, files in os.walk(args.src):
        for file in files:
            local_path = osp.join(root, file)
            remote_path = osp.join(args.dst, local_path[len(args.src):])
            print(local_path, remote_path)

            thread = CheckMD5Thread(client, local_path, remote_path)
            thread.start()
            threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='remote server host')
    parser.add_argument('--port', type=int, help='remote server port')
    parser.add_argument('--username', type=str, help='remote server username')
    parser.add_argument('--password', type=str, help='remote server password')
    parser.add_argument('--src', type=str, help='source file or directory')
    parser.add_argument('--dst', type=str, help='destination file or directory')
    args = parser.parse_args()

    main(args)