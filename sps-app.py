import sys
import subprocess
import os
import argparse
from deployhelpers import print_dots, deploy, reset_application, reset_app_version

# Get the full path of the executable file
exe_path = os.path.abspath(__file__)

# Construct the full path of the "options.json" file
options_path = os.path.join(os.path.dirname(exe_path), "options.json")
persistent_volume_path = os.path.join(os.path.dirname(exe_path), "pvc.json")

def show_spsApp_help():
  print("usage: sps-app [command]\n\
deploy          Deploy a new build\n\
reset           Reset an application\n\
update          Update options for an application\n\
delete          Delete an application\n\
shell           Open a shell to the VM\n\
config          Set the SPS server\n\
restart-server  Restarts a dedicated server\n\
-h, --help    Show help menu\n\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app reset demo")

def show_reset_help():
  print("Resets the client application\n\
usage: sps-app reset <branch> [options...]\n\
-t, --tag       The existing application version to reset to\n\
-h, --help      Show help menu\n\
Example: sps-app reset demo\n\
Example: sps-app reset demo --tag 23-04-20_build-A_CD_PalatialTest")

def show_delete_help():
  print("Deletes the application\n\
usage: sps-app delete <branch>\n\
-h, --help,     Show help menu\n\n\
Example: sps-app delete prophet")

def show_shell_help():
  print("usage: sps-app shell\n\
Example: sps-app shell")

def show_config_help():
  print("usage: sps-app config [command]\n\
update   Change the credentials for the current SPS server\n\
   -p, --key, --access-key, --password    The API key for the SPS server\n\
get-key  Get the API key for the SPS server\n\
\n\
Example: sps-app config update --access-key ez2UroRWSJpEkahedev80neMGOGrDo6U\n\
Example: sps-app config get-key\n\
output: ez2UroRWSJpEkahedev80neMGOGrDo6U")

def show_update_help():
  print("Updates the application's configuration\n\
\n\
usage: sps-app update <branch> [options...]\n\
    --add-volume-mount    Adds a storage volume to the application mounted at /home/ue4/\n\
    --remove-volume-mount Removes the storage volume\n\
-h, --help                Show help menu\n\
\n\
To see more options, type \"sps-client application update\"\n\
\n\
Example: sps-app update prophet overProvisioning.instances \"3\"")

def show_resetServer_help():
  print("usage: sps-app restart-server <branch>\n\
-h, --help      Show help menu\n\n\
Example: sps-app restart-server banyan")

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

def delete_application(branch):
  print(f"Delete {branch}...")
  subprocess.run(f'sps-client application delete --name {branch}')

if len(sys.argv) < 2 or sys.argv[1] != "deploy" and sys.argv[1] != "reset" and sys.argv[1] != "update" and sys.argv[1] != "delete" and sys.argv[1] != "restart-server" and sys.argv[1] != "shell" and sys.argv[1] != "config":
  show_spsApp_help()
  sys.exit(1)

update_options = [
  "--add-volume-mount",
  "--remove-volume-mount",
  "-h", "--help",
  "--activeVersion", 
]

command = sys.argv[1];

if command == "deploy":
  # Retrieve values from sys.argv starting from index 3 onward
  values = sys.argv[2:]
  
  # Convert the list of values into a string
  values_str = ' '.join(values)

  deploy(values_str)

elif command == "reset":
  if len(sys.argv) < 3:
    show_reset_help()
    sys.exit(1)
  for elem in sys.argv[2:]:
    if elem == "-h" or elem == "--help":
      show_reset_help()
      sys.exit(0)
  branch = sys.argv[2]
  image_tag = None
  if len(sys.argv) == 5 and (sys.argv[3] == "-t" or sys.argv[3] == "--tag"):
    image_tag = f"{branch}:{sys.argv[4]}"
  reset_application(branch, image_tag)

elif command == "delete":
  if len(sys.argv) < 3 or sys.argv[2] == "-h" or sys.argv[2] == "--help":
    show_delete_help()
    sys.exit(0)
  branch = sys.argv[2]
  delete_application(branch)

elif command == "update":
  if len(sys.argv) < 3:
    show_update_help()
    sys.exit(1)
  branch = sys.argv[2]
  added = False
  removed = False

  for elem in sys.argv[2:]:
    if elem == "-h" or elem == "--help":
      show_update_help()
      sys.exit(0)
  for elem in sys.argv[3:]:
    if elem == "--add-volume-mount":
      if removed:
        print("error: already removed the volume, can't add in the same command")
        sys.exit(1)
      reset_app_version(branch, persistent_volume_path)
      added = True
    if elem == "--remove-volume-mount":
      if added:
        print("error: already added the volume, can't remove in the same command")
        sys.exit(1)
      reset_app_version(branch)
      removed = True
  rest = sys.argv[3:]
  rest[:] = [elem for elem in rest if elem not in update_options]
  if rest:
    subprocess.run(f"sps-client application update --name {branch} " + " ".join(sys.argv[3:]))
elif command == "restart-server":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    show_resetServer_help()
    sys.exit(0)
  if len(sys.argv) < 3 or len(sys.argv) > 3:
    show_resetServer_help()
    sys.exit(0)
  branch = sys.argv[2]
  reset_server(branch)
elif command == "shell":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    show_shell_help()
    sys.exit(0)
  if len(sys.argv) > 3:
    show_shell_help()
    sys.exit(1)
  subprocess.run('ssh david@prophet.palatialxr.com')
elif command == "config":
  if len(sys.argv) < 3 or (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    show_config_help()
    sys.exit(0)

  if sys.argv[2] == "update":
    if len(sys.argv) != 5:
      show_config_help()
      sys.exit(0)
    if sys.argv[3] == "--password" or sys.argv[3] == "-p" or sys.argv[3] == "--access-key" or sys.argv[3] == "--key":
      subprocess.run("sps-client config delete --name palatial-sps-server")
      subprocess.run("sps-client config add --name palatial-sps-server --address \"https://api.tenant-palatial-platform.lga1.ingress.coreweave.cloud\" --access-key " + sys.argv[4])
      subprocess.run("sps-client config set-default --name palatial-sps-server")
  elif sys.argv[2] == "get-key":
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
      print(output)
  else:
    show_config_help()
    sys.exit(0)
else:
  for i in range(1, len(sys.argv)):
    opt = sys.argv[i]
    if opt == "--help" or opt == "-h" or opt == "help":
      show_spsApp_help()