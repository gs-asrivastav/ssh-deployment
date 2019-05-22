import math
import os
from time import sleep
from typing import Tuple

import paramiko
from tqdm import tqdm


def connect(*args, **kwargs):
    ssh_client: paramiko.SSHClient = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(*args, **kwargs)
    return ssh_client


def execute_command(ssh_client: paramiko.SSHClient, command: str, *args, **kwargs) -> Tuple[
    paramiko.channel.ChannelFile, paramiko.channel.ChannelFile, paramiko.channel.ChannelStderrFile]:
    stdin, stdout, stderr = ssh_client.exec_command(command, *args, **kwargs)

    stdin: paramiko.channel.ChannelFile = stdin
    stdout: paramiko.channel.ChannelFile = stdout
    stderr: paramiko.channel.ChannelStderrFile = stderr

    return stdin, stdout, stderr


def print_console(stdout: paramiko.channel.ChannelFile, stderr: paramiko.channel.ChannelFile) -> None:
    std_out_content = '\n'.join(list(map(lambda x: x.replace('\n', ''), stdout.readlines())))
    std_err_content = '\n'.join(list(map(lambda x: x.replace('\n', ''), stderr.readlines())))
    print(f"Output(s):\n{std_out_content}\nError(s):\n{std_err_content}")


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def tqdm_progress_bar(*args, **kwargs):
    # https://github.com/tqdm/tqdm/issues/311
    pbar = tqdm(*args, **kwargs)
    last = [0]

    def view_bar_cb(a, b):
        pbar.total = int(b)
        pbar.update(int(a - last[0]))
        last[0] = a

    return view_bar_cb, pbar


if __name__ == '__main__':
    sleep_seconds = 45
    target_file = 'gs-spring-boot-distribution.zip'
    # Enter path to distribution zip file here.
    target_dir = '/Users/asrivastava/Documents/Userdata/Gainsight/BI/bi-web/target'
    remote_base_dir = 'bi-web'

    # You could hardcode the username/password
    client = connect(hostname='queryapi-dev2.develgs.com', username=os.getenv('username'),
                     password=os.getenv('password'))
    stdin, stdout, stderr = execute_command(client, f'rm -rf {remote_base_dir}/{target_file}')
    print_console(stdout, stderr)

    sftp: paramiko.SFTPClient = client.open_sftp()
    cbk, pbar = tqdm_progress_bar(ascii=True, unit='b', unit_scale=True)
    sftp.put(f"{target_dir}/{target_file}", f"{remote_base_dir}/{target_file}", callback=cbk)
    sftp.close()

    print("Killing previous instance of bi-web application")
    stdin, stdout, stderr = execute_command(client, f'pkill -f com.gainsight.bi.GSReportingWebAp')
    print_console(stdout, stderr)

    print(f"Moving to {remote_base_dir} and starting up application.")
    stdin, stdout, stderr = execute_command(client, f'cd {remote_base_dir} && pwd && sh setup.sh', bufsize=256)
    print_console(stdout, stderr)

    print(f"Initiating sleep for {sleep_seconds} seconds")
    sleep(sleep_seconds)
    print(f"Executing curl request to the application for status.")
    stdin, stdout, stderr = execute_command(client, f'curl -X GET --url http://localhost:9050/v3/bi/status')
    print_console(stdout, stderr)
