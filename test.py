import traceback
from pathlib import Path

from paramiko import SSHClient, AutoAddPolicy, SFTPClient

username = "tc"
password = "123"
vma_ip = "192.168.56.106"
vmb_ip = "192.168.56.107"
vmc_ip = "192.168.56.108"
remote_python_interpreter = "/usr/local/bin/python3"
remote_working_dir = "/home/tc/workplace/cw1/"
files_to_deploy = ["main.py", "config.py", "sync_drive/"]
file_exclusion = ["__pycache__"]


def init(ssh: SSHClient, sftp: SFTPClient):
    # create working dir
    ssh.exec_command(
        f"if [ ! -d \"/home/{username}/workplace\" ]; then\nmkdir -p /home/{username}/workplace\necho {password} | sudo mount /mnt/sda1 /home/{username}/workplace\nfi")
    ssh.exec_command(f"echo {password} | sudo chown -R {username} /home/{username}/workplace")
    ssh.exec_command(f"cd /home/{username}/workplace")
    ssh.exec_command(f"rm -r {remote_working_dir}")
    ssh.exec_command(f"mkdir -p {remote_working_dir}")

    # upload code
    def upload_dir(local, remote):
        for kw in file_exclusion:
            if kw in local:
                return
        print(f"uploading {local} to {remote}")
        sftp.mkdir(str(Path(remote).joinpath(local)))
        for i in Path(local).rglob("*"):
            if i.is_dir():
                upload_dir(str(i), remote)
            else:
                upload_file(str(i), str(Path(remote).joinpath(i)))

    def upload_file(local: str, remote: str):
        for kw in file_exclusion:
            if kw in local:
                return
        print(f"uploading {local} to {remote}")
        sftp.put(local, remote)

    for i in files_to_deploy:
        path = Path(i)
        if path.is_dir():
            upload_dir(i, str(Path(remote_working_dir)))
        else:
            upload_file(i, str(Path(remote_working_dir).joinpath(i)))


def main():
    # connect
    try:
        ssh_a = SSHClient()
        ssh_b = SSHClient()
        ssh_c = SSHClient()
        ssh_a.set_missing_host_key_policy(AutoAddPolicy())
        ssh_b.set_missing_host_key_policy(AutoAddPolicy())
        ssh_c.set_missing_host_key_policy(AutoAddPolicy())
        ssh_a.connect(vma_ip, username=username, password=password, port=22, timeout=5)
        ssh_b.connect(vmb_ip, username=username, password=password, port=22, timeout=5)
        ssh_c.connect(vmc_ip, username=username, password=password, port=22, timeout=5)
        sftp_a = ssh_a.open_sftp()
        sftp_b = ssh_b.open_sftp()
        sftp_c = ssh_c.open_sftp()

        init(ssh_a, sftp_a)
        init(ssh_b, sftp_b)
        init(ssh_c, sftp_c)
    except:
        traceback.print_exc()


if __name__ == '__main__':
    main()
