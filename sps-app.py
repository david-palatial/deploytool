import sys
import subprocess
import os
import argparse
import json
import re
import shutil
import paramiko
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import misc
import help_menus
import deployhelpers
import shlex

# Get the full path of the executable file
exe_path = os.path.abspath(__file__)

# Construct the full path of the "options.json" file
options_path = os.path.join(os.path.dirname(exe_path), "options.json")
persistent_volume_path = os.path.join(os.path.dirname(exe_path), "pvc.json")
config_file = os.path.join(os.path.dirname(exe_path), "dist", "config")

def copy_config_to_kube():
  # Check if the config file exists
  if os.path.isfile(config_file):
    kube_dir = os.path.join(os.environ.get("USERPROFILE"), ".kube")

    # Create .kube folder if it doesn't exist
    if not os.path.exists(kube_dir):
      os.makedirs(kube_dir)

    # Copy the config file to .kube folder
    shutil.copy2(config_file, kube_dir)
    print("Config file copied successfully.")
  else:
    print("Config file does not exist.")

def download_kubectl():
  code = "& $([scriptblock]::Create((New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/coreweave/kubernetes-cloud/master/getting-started/k8ctl_setup.ps1'))) -Silent"
  powershell_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", code]
  subprocess.run(powershell_cmd, shell=True)

def GetKey():
  ps_code = r'''
    $base64 = (kubectl get secrets/sps-api-access-key --template='{{.data.restapiaccesskey}}')
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($base64))
    '''

  # Execute PowerShell code using subprocess
  result = subprocess.run(['powershell', '-Command', ps_code], capture_output=True, text=True)

  # Check the result
  if result.returncode == 0:
    # PowerShell command executed successfully
    output = result.stdout.strip()
    return output
  return None

def tag_has_repo(tag):
    parts = tag.split(':')
    return len(parts) == 2 and all(parts)

def reset_server(branch):
  subprocess.run(f'ssh david@prophet.palatialxr.com "sudo systemctl restart server_{branch}"')

def commandExists(opt, options_list):
  if opt in options_list:
    return True
  try:
    subprocess.run(f'sps-client application update --name example {opt}')
    return True
  except subprocess.CalledProcessError as e:
    return False
  return False

def generate_ssh_key_pair():
    private_key_path = os.path.expanduser("~/.ssh/id_rsa")
    public_key_path = private_key_path + ".pub"

    # Check if the key pair already exists
    if os.path.isfile(private_key_path) and os.path.isfile(public_key_path):
        print("SSH key pair already exists.")
        return

    # Generate a new key pair
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Save the private key
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save the public key
    public_key = private_key.public_key()
    with open(public_key_path, "wb") as f:
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        f.write(public_key_bytes)


    # Print the public key if created
    if public_key_bytes:
        print("SSH key pair generated successfully.")
        print("Send this public key to David:")
        print(public_key_bytes.decode())

def is_kubectl_installed():
    try:
        subprocess.run(['kubectl'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def delete_application(branch):
  print(f"Delete {branch}...")
  subprocess.run(f'sps-client application delete --name {branch}')

if len(sys.argv) < 2 or sys.argv[1] != "deploy" and sys.argv[1] != "reset" and sys.argv[1] != "update" and sys.argv[1] != "delete" and sys.argv[1] != "create" and sys.argv[1] != "restart-server" and sys.argv[1] != "shell" and sys.argv[1] != "config" and sys.argv[1] != "setup" and sys.argv[1] != "restart-webpage" and sys.argv[1] != "restart" and sys.argv[1] != "version-info":
  help_menus.show_spsApp_help()
  sys.exit(1)

update_options = [
  "--add-volume-mount",
  "--remove-volume-mount",
  "-h", "--help",
  "--activeVersion",
  "--overProvisioning"
]

command = sys.argv[1];

if command == "deploy":
  # Retrieve values from sys.argv starting from index 3 onward
  values = sys.argv[2:]
  
  # Convert the list of values into a string
  values_str = ' '.join(values)
  
  deployhelpers.deploy(values)

elif command == "reset" or command == "restart":
  if len(sys.argv) < 3:
    help_menus.show_reset_help()
    sys.exit(1)
  for elem in sys.argv[2:]:
    if elem == "-h" or elem == "--help":
      help_menus.show_reset_help()
      sys.exit(0)
  branch = sys.argv[2]
  image_tag = None
  if len(sys.argv) == 5 and (sys.argv[3] == "-t" or sys.argv[3] == "--tag"):
    tag = sys.argv[4]
    if not tag_has_repo(tag):
      image_tag = f"{branch}:{tag}"
  deployhelpers.reset_application(branch, image_tag)

elif command == "delete":
  if len(sys.argv) < 3 or sys.argv[2] == "-h" or sys.argv[2] == "--help":
    help_menus.show_delete_help()
    sys.exit(0)
  branch = sys.argv[2]
  delete_application(branch)
  subprocess.run(f'ssh {misc.host} ./deployment/cleanup.sh {branch}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

elif command == "create":
  if len(sys.argv) < 3 or sys.argv[2] == "-h" or sys.argv[2] == "--help":
    help_menus.show_create_help()
    sys.exit(0)

  branch = sys.argv[2]
  exists, data = misc.try_get_application(branch)
  if not exists:
    subprocess.run(f'sps-client application create --name {branch}')
  elif "activeVersion" in data["response"]:
    print(f"error: {branch} already exists with an active version")
    sys.exit(1)

  if len(sys.argv) > 3:
    args = sys.argv[3:]
    tag = None
    version = None
    for i in range(0, len(args)):
      if args[i] == "-t" or args[i] == "--tag":
        if i + 1 >= len(args):
          print(f"error: {args[i]} requires an argument")
          sys.exit(1)
        tag = args[i+1]
      elif args[i] == "--vn" or args[i] == "--version-name":
        if i + 1 >= len(args):
          print(f"error: {args[i]} requires an argument")
          sys.exit(1)
        version = args[i+1]
      elif args[i] == "-h" or args[i] == "--help":
        help_menus.show_create_help()
        sys.exit(0)

    if tag == None and version != None:
      print(f"error: can't create a version without a tag. either provide one with -t or --tag, or deploy a new build with 'sps-app deploy <dir> -b {branch}'")
      sys.exit(1)
    elif tag == None:
      print("error: invalid argument supplied")
      sys.exit(1)

    repo = branch
  
    if tag_has_repo(tag):
      repo = tag.split(':')[0]
      tag = tag.split(':')[1]

    version = tag if version == None else version
    deployhelpers.set_new_version(branch, version, f'docker.io/dgodfrey206/{repo}:{tag}')

    data = { "uploader": { "sourceDirectory": "n/a" } }
    save_version_info(branch, data, client=True)

elif command == "update":
  if len(sys.argv) < 3:
    help_menus.show_update_help()
    sys.exit(1)
  branch = sys.argv[2]
  added = False
  removed = False

  for elem in sys.argv[2:]:
    if elem == "-h" or elem == "--help":
      help_menus.show_update_help()
      sys.exit(0)

  for elem in sys.argv[3:]:
    if elem == "--add-volume-mount":
      if removed:
        print("error: already removed the volume, can't add in the same command")
        sys.exit(1)
      deployhelpers.reset_app_version(branch, persistent_volume_path)
      added = True
    if elem == "--remove-volume-mount":
      if added:
        print("error: already added the volume, can't remove in the same command")
        sys.exit(1)
      deployhelpers.reset_app_version(branch)
      removed = True

  rest = sys.argv[3:]
  rest_not_in_options = [elem for elem in rest if elem not in update_options]
  if rest_not_in_options:
    subprocess.run(f"sps-client application update --name {branch} " + " ".join(rest_not_in_options))
elif command == "restart-server":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_resetServer_help()
    sys.exit(0)
  if len(sys.argv) < 3 or len(sys.argv) > 3:
    help_menus.show_resetServer_help()
    sys.exit(0)
  branch = sys.argv[2]
  reset_server(branch)
elif command == "shell":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_shell_help()
    sys.exit(0)
  if len(sys.argv) > 3:
    help_menus.show_shell_help()
    sys.exit(1)
  subprocess.run(f'ssh {misc.host}')
elif command == "config":
  if len(sys.argv) < 3 or (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_config_help()
    sys.exit(0)

  if sys.argv[2] == "update":
    region = "lga1"
    if len(sys.argv) < 4:
      help_menus.show_config_help()
      sys.exit(0)
    if sys.argv[3] == "--password" or sys.argv[3] == "-p" or sys.argv[3] == "--access-key" or sys.argv[3] == "--key" or sys.argv[3] == "--auto":
      key = None
      r = None
      if sys.argv[3] == "--auto":
        key = GetKey()
        if len(sys.argv) == 5:
          r = sys.argv[4]
      else:
        key = sys.argv[4]

      if len(sys.argv) == 6:
        r = sys.argv[5]
      if r == "--lga":
        region = "lga1"
      elif r == "--ord":
        region = "ord1"
      elif r == "--las":
        region = "las1"
      if key == None:
        print("--auto requires 'sps-app setup' first")
        sys.exit(1)
      subprocess.run("sps-client config delete --name palatial-sps-server")
      subprocess.run(f"sps-client config add --name palatial-sps-server --address \"https://api.tenant-palatial-platform.{region}.ingress.coreweave.cloud\" --access-key " + key)
      subprocess.run("sps-client config set-default --name palatial-sps-server")
      
  elif sys.argv[2] == "get-key":
    key = GetKey()
    if key == None:
      print("Unable to access REST API server")
    else:
      print(key)
  else:
    help_menus.show_config_help()
    sys.exit(0)
elif command == "setup":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_setup_help()
    sys.exit(0)
  subprocess.run("image-builder auth --username dgodfrey206 --password applesauce --registry 'https://index.docker.io/v1/'")
  #if GetKey() == None:
  #  download_kubectl()
  #  copy_config_to_kube()
  print("\nCopy the API key from https://apps.coreweave.com/#/c/default/ns/tenant-palatial-platform/apps/helm.packages/v1alpha1/palatial-sps-server and paste it below\n")
  key = input("API Key: ")
  subprocess.run("sps-client config add --name palatial-sps-server --address \"https://api.tenant-palatial-platform.lga1.ingress.coreweave.cloud\" --access-key " + key)
  generate_ssh_key_pair()
elif command == "restart-webpage":
  if len(sys.argv) == 2 or len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_Restart_Webpage_help()
    sys.exit(0)
  subprocess.run(f'ssh david@prophet.palatialxr.com "sudo systemctl restart dom_{sys.argv[2]}"')
elif command == "version-info":
  if len(sys.argv) == 2 or len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_Version_Info_help()
    sys.exit(0)
  branch = sys.argv[2]
  exists, data = misc.try_get_application(branch)
  if not exists:
    print(f"error: application {branch} does not exist")
    sys.exit(1)
  if not "activeVersion" in data["response"]:
    print("No active version info for this application")
  else:
    remote_client_path = f'/usr/local/bin/cw-app-logs/{branch}/client/activeVersion.log'
    remote_server_path = f'/usr/local/bin/cw-app-logs/{branch}/server/activeVersion.log'
    if misc.file_exists_on_remote(misc.host, remote_client_path):
      print("Client info:")
      result = subprocess.run(f'ssh {misc.host} cat {remote_client_path}', stdout=subprocess.PIPE)
      print(result.stdout.decode('utf-8'))
    else:
      print("No version information saved for client")

    if misc.file_exists_on_remote(misc.host, remote_server_path):
      print("Server info:")
      result = subprocess.run(f'ssh {misc.host} cat {remote_server_path}', stdout=subprocess.PIPE)
      print(result.stdout.decode('utf-8'))
    else:
      print("No version information saved for server")

else:
  for i in range(1, len(sys.argv)):
    opt = sys.argv[i]
    if opt == "--help" or opt == "-h" or opt == "help":
      help_menus.show_spsApp_help()