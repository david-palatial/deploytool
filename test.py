import paramiko
import os

def execute_ssh_command(command):
  home_directory = os.path.expanduser("~")
  hostname = "palatial.tenant-palatial-platform.coreweave.cloud"
  port = 22
  username = "david"
  private_key_path = os.path.join(home_directory, ".ssh", "id_rsa")

  client = paramiko.SSHClient()
  client.load_system_host_keys()

  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  try:
    client.connect(hostname, port, username, key_filename=private_key_path)
    stdin, stdout, stderr = client.exec_command(command)
    if stderr.channel.recv_exit_status() != 0:
      raise Exception(f"Failure executing the remote script: {stderr.read().decode()}")
    return stdout.read().decode()
  except Exception as e:
    return None
  finally:
    client.close()

x = execute_ssh_command("test -d palatial-web && echo True || echo False")
print(x)