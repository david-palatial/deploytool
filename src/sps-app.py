import sys
import subprocess
import os
import json
import re
import shutil
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import misc
import help_menus
import deployhelpers
from dotenv import dotenv_values
import getpass
from datetime import datetime

exe_path = misc.get_exe_directory()
env_values = dotenv_values(os.path.join(exe_path, ".env"))
env_path = os.path.join(exe_path, ".env")

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
    print("output = " + output)
    return output
  return None

def tag_has_repo(tag):
    parts = tag.split(':')
    return len(parts) == 2 and all(parts)

def reset_server(branch):
  subprocess.run(f'ssh {misc.host} "sudo systemctl restart server_{branch}"')

def commandExists(opt, options_list):
  if opt in options_list:
    return True
  try:
    subprocess.run(f'sps-client application update --name example {opt}')
    return True
  except subprocess.CalledProcessError as e:
    return False
  return False

def requiredInput(msg):
  value = None
  while True:
    value = input(msg)
    if value:
      break
  return value

def generate_ssh_key_pair():
    private_key_path = os.path.expanduser("~/.ssh/id_rsa")
    public_key_path = private_key_path + ".pub"

    # Check if the key pair already exists
    if os.path.isfile(private_key_path) and os.path.isfile(public_key_path):
        print("\nSSH key pair already exists. Skipping generation...\n")
        key = None
        with open(public_key_path, "r") as f:
          key = f.read()
        return key
 
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
        return public_key_bytes.decode()

def custom_password_input(prompt="Password: "):
    password = ""
    while True:
        char = getpass.getpass(prompt='', stream=None)
        if not char:
            break
        password += char
        print('*')
    return password

def is_kubectl_installed():
    try:
        subprocess.run(['kubectl'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def delete_applications(apps, client_only=False):
  if client_only:
    for i in range(0, len(apps)):
      print(f"Delete {apps[i]}...")
      subprocess.run(f'sps-client application delete --name {apps[i]}')
  else:
    branches = ' '.join(apps)
    subprocess.run(f'ssh {misc.host} ./link-deployment/util/cleanup.sh {branches}')

def reload_env_file(env_path, values):
  with open(env_path, 'w') as f:
    for k, v in values.items():
      f.write(f"{k}={v}\n")

def process_config_argument(args, opt, envVar, i, len):
  if args[i] == opt:
    if opt.endswith("password-stdin"):
      env_values[envVar] = getpass.getpass("Password: ")
      return
    if i + 1 >= len:
      if i == 0:
        print(env_values[envVar])
        sys.exit(0)
    else:
      if args[i+1].startswith("-"):
        print(f"error: {opt} used without an argument")
        sys.exit(0)
      else:
        env_values[envVar] = args[i+1]
        print(envVar + " set to " + args[i+1])

if len(sys.argv) < 2 or sys.argv[1] not in ["deploy", "reset", "update", "delete", "create", "restart-server", "shell", "config", "setup", "restart-webpage", "restart", "version-info", "enable", "disable", "create-link"]:
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

  if "-h" in sys.argv or "--help" in sys.argv:
    help_menus.show_reset_help()
    sys.exit(1)

  branch = sys.argv[2]
  container_tag = None
  version = None

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
        help_menus.show_reset_help()
        sys.exit(0)

    repo = branch
  
    if tag_has_repo(tag):
      repo = tag.split(':')[0]
      tag = tag.split(':')[1]

    container_tag = f'{env_values["REPOSITORY_URL"]}/{repo}:{tag}'

  deployhelpers.reset_application(branch, version=version, container_tag=container_tag)

  data = { "uploader": { "sourceDirectory": "n/a" } }
  #misc.save_version_info(branch, data, client=True)

elif command == "delete":
  if len(sys.argv) < 3 or "-h" in sys.argv or "--help" in sys.argv:
    help_menus.show_delete_help()
    sys.exit(0)

  client_only = True
  upper = len(sys.argv)

  if len(sys.argv) > 3:
    if sys.argv[-1].lower() == "--full":
      client_only = False
      upper -= 1

  apps = sys.argv[2:upper]
  delete_applications(apps, client_only=client_only)

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

    if version == None:
      highestVersion = misc.get_highest_version(misc.get_versions(branch))
      if highestVersion == None:
        version = "v0-0-1"
      else:
        version = misc.increment_version(highestVersion)

    deployhelpers.set_new_version(branch, version, container_tag=f'{env_values["REPOSITORY_URL"]}/{repo}:{tag}')

    data = { "uploader": { "sourceDirectory": "n/a" } }
    #misc.save_version_info(branch, data, client=True)

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

  if len(sys.argv) == 3 and sys.argv[2] == "--fetch-api-key":
    key = env_values['API_KEY'] = GetKey()
    if not key:
      print(f"error: could not fetch key. copy the API key from https://apps.coreweave.com/#/c/default/ns/{env_values['COREWEAVE_NAMESPACE']}/apps/helm.packages/v1alpha1/{env_values['SPS_REST_API_SERVER']} and run 'sps-app config --api-key <key>' instead")
    else:
      print(key)
  elif len(sys.argv) == 3 and sys.argv[2] == "--list":
    print("Registry username: " + env_values['REGISTRY_USERNAME'])
    print("Registry password: " + env_values['REGISTRY_PASSWORD'])
    print("Coreweave namespace: " + env_values['COREWEAVE_NAMESPACE'])
    print("Base repo URL: " + env_values['REPOSITORY_URL'])
    print("Registry API endpoint: " + env_values['IMAGE_REGISTRY_API'])
    print("API key: " + env_values['API_KEY'])
  else:
    args = sys.argv[2:]
    current_registry_username = env_values['REGISTRY_USERNAME']
    current_repository_url = env_values['REPOSITORY_URL']
    
    region = env_values['REGION']
    namespace = env_values['COREWEAVE_NAMESPACE']
    api_server = env_values['SPS_REST_API_SERVER']
    api_key = env_values['API_KEY']

    for i in range(0, len(args)):
      process_config_argument(args, "--registry-username",       'REGISTRY_USERNAME',   i, len(args))
      process_config_argument(args, "--registry-password",       'REGISTRY_PASSWORD',   i, len(args))
      process_config_argument(args, "--registry-password-stdin", 'REGISTRY_PASSWORD',   i, len(args))
      process_config_argument(args, "--coreweave-namespace",     'COREWEAVE_NAMESPACE', i, len(args))
      process_config_argument(args, "--region",                  'REGION',              i, len(args))
      process_config_argument(args, "--server-name",             'SPS_REST_API_SERVER', i, len(args))
      process_config_argument(args, "--repository-url",          'REPOSITORY_URL',      i, len(args))
      process_config_argument(args, "--registry-endpoint",       'IMAGE_REGISTRY_API',  i, len(args))
      process_config_argument(args, "--api-key",                 'API_KEY',             i, len(args))

    if len(sys.argv) < 4:
      sys.exit(0)

    if current_registry_username != env_values['REGISTRY_USERNAME'] and current_repository_url == env_values['REPOSITORY_URL']:
      if "docker" in current_repository_url:
        env_values['REPOSITORY_URL'] = f"docker.io/{env_values['REGISTRY_USERNAME']}"
      else:
        new_repo_url = None
        while not new_repo_url:
          new_repo_url = input("Enter your new repository url (ex. docker.io/username/): ")
        env_values['REPOSITORY_URL'] = new_repo_url.trim("/")

    if region != env_values['REGION'] or namespace != env_values['COREWEAVE_NAMESPACE'] or api_server != env_values['SPS_REST_API_SERVER'] or api_key != env_values['API_KEY']:
      sps_rest_api_address = f"https://api.{env_values['COREWEAVE_NAMESPACE']}.{env_values['REGION']}.ingress.coreweave.cloud/"

      output = subprocess.run(f"sps-client config delete --name {env_values['SPS_REST_API_SERVER']}", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      result = output.stdout
      if output.stderr:
        result = output.stderr

      result = result.decode('utf-8')
      if not "already exists" in result:
        print(result)

      subprocess.run(f"sps-client config add --name {env_values['SPS_REST_API_SERVER']} --address {sps_rest_api_address} --access-key " + env_values['API_KEY'])
      subprocess.run(f"sps-client config set-default --name {env_values['SPS_REST_API_SERVER']}")

    env_values['REPOSITORY_URL'] = env_values['REPOSITORY_URL'].strip('/')
    reload_env_file(env_path, env_values)
elif command == "setup":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_setup_help()
    sys.exit(0)

  force = len(sys.argv) == 3 and (sys.argv[2] == "-f" or sys.argv[2] == "--force")

  if not force and os.path.exists(env_path):
    print("sps-app is already set up. To update specific settings see sps-app config --help")
    sys.exit(0)

  env_values = dotenv_values(os.path.join(exe_path, 'default.env'))

  server = input(f"SPS server name [{env_values['SPS_REST_API_SERVER']}]: ")
  username = requiredInput(f"Image registry username: ")
  password = requiredInput(f"Image registry password: ")
  image_registry_api = requiredInput(f"Image registry API endpoint (i.e https://index.docker.io/v2/): ")
  default_repo_url = None
  if "docker" in image_registry_api:
    default_repo_url = f'docker.io/{username}'
  repo_url = input(f"Repository URL [{default_repo_url}]: ")
  region = input(f"Region [{env_values['REGION']}]: ")
  namespace = input(f"Namespace [{env_values['COREWEAVE_NAMESPACE']}]: ")

  if server:
    env_values['SPS_REST_API_SERVER'] = server

  env_values['REGISTRY_USERNAME'] = username
  env_values['REGISTRY_PASSWORD'] = password
  env_values['IMAGE_REGISTRY_API'] = image_registry_api if image_registry_api else default_repo_url
  env_values['REPOSITORY_URL'] = repo_url.strip('/') if repo_url else default_repo_url

  if region:
    env_values['REGION'] = region
  if namespace:
    env_values['COREWEAVE_NAMESPACE'] = namespace

  key = GetKey()
  
  while not key:
    print(f"Copy the API key from https://apps.coreweave.com/#/c/default/ns/{env_values['COREWEAVE_NAMESPACE']}/apps/helm.packages/v1alpha1/{env_values['SPS_REST_API_SERVER']} and paste it below")
    key = input(f"API Key: ")

  env_values['API_KEY'] = key
  reload_env_file(env_path, env_values)
  print("Hello")

  sps_rest_api_address = f"https://api.{env_values['COREWEAVE_NAMESPACE']}.{env_values['REGION']}.ingress.coreweave.cloud/"

  subprocess.run(f"image-builder auth --username {env_values['REGISTRY_USERNAME']} --password {env_values['REGISTRY_PASSWORD']} --registry {env_values['IMAGE_REGISTRY_API']}")

  output = subprocess.run(f"sps-client config add --name {env_values['SPS_REST_API_SERVER']} --address {sps_rest_api_address} --access-key " + env_values['API_KEY'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  result = output.stdout

  if output.stderr:
    result = output.stderr

  result = result.decode('utf-8')
  if not "already exists" in result:
    print(result)
  
  subprocess.run(f"sps-client config set-default --name {env_values['SPS_REST_API_SERVER']}")
  key = generate_ssh_key_pair()
  if key:
    print("===> Setup is complete. Send this public key to David: \n")
    print(key)
elif command == "restart-webpage":
  if len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_Restart_Webpage_help()
    sys.exit(0)
  subprocess.run(f'ssh {misc.host} "sudo systemctl restart react-dom"')
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
    remote_client_path = f'/var/log/cw-app-logs/{branch}/client/activeVersion.log'
    remote_server_path = f'/var/log/cw-app-logs/{branch}/server/activeVersion.log'
    if misc.file_exists_on_remote(misc.host, remote_client_path):
      print("Client info:")
      result = subprocess.run(f'ssh {misc.host} cat {remote_client_path}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print(result.stdout.decode('utf-8'))
    else:
      print("No version information saved for client")

    if misc.file_exists_on_remote(misc.host, remote_server_path):
      print("Server info:")
      result = subprocess.run(f'ssh {misc.host} cat {remote_server_path}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print(result.stdout.decode('utf-8'))
    else:
      print("No version information saved for server")
elif command == "disable":
  if len(sys.argv) == 2 or len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_disable_help()
    sys.exit(0)
  app = sys.argv[2]
  exists, data = misc.try_get_application(app)
  if not exists:
    print(f"error: {app} does not exist")
    sys.exit(1)

  print(f'statefulset.apps/sps-signalling-server-{app} scaled')
  subprocess.run(f'kubectl scale statefulset sps-signalling-server-{app} --replicas=0', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  
  print(f'deployment.apps/sps-auth-{app} scaled')
  subprocess.run(f'kubectl scale deployment sps-auth-{app} --replicas=0', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f'deployment.apps/sps-instance-manager-{app} scaled')
  subprocess.run(f'kubectl scale deployment sps-instance-manager-{app} --replicas=0', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  subprocess.run(f"sps-client application update -n {app} --activeVersion \"\"", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f"Stopping unit server_{app}.service...")
  subprocess.run(f'ssh {misc.host} sudo systemctl stop server_{app}')

elif command == "enable":
  if len(sys.argv) == 2 or len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_enable_help()
    sys.exit(0)
  app = sys.argv[2]

  exists, data = misc.try_get_application(app)
  if not exists:
    print(f"error: {app} does not exist")
    sys.exit(1)
  if "activeVersion" in data["response"]:
    print(f"error: {app} already has an active version")
    sys.exit(1)

  versions = misc.get_version_objects(app)
  time_strings = [ x["timeCreated"] for x in versions ]
  datetime_objects = [datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %z %Z") for time_str in time_strings]

  # Find the latest datetime
  latest_datetime = max(datetime_objects)

  # Get the index of the latest datetime
  latest_datetime_index = datetime_objects.index(latest_datetime)

  subprocess.run(f'sps-client application update -n {app} --activeVersion {versions[latest_datetime_index]["name"]}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f'deployment.apps/sps-instance-manager-{app} scaled')
  subprocess.run(f'kubectl scale deployment sps-instance-manager-{app} --replicas=1', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f'deployment.apps/sps-auth-{app} scaled')
  subprocess.run(f'kubectl scale deployment sps-auth-{app} --replicas=1', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  print(f'statefulset.apps/sps-signalling-server-{app} scaled')
  subprocess.run(f'kubectl scale statefulset sps-signalling-server-{app} --replicas=1', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print(f"Starting unit server_{app}.service...")
  subprocess.run(f'ssh {misc.host} sudo systemctl start server_{app}')
elif command == "create-link":
  if len(sys.argv) == 2 or len(sys.argv) == 3 and (sys.argv[2] == "-h" or sys.argv[2] == "--help"):
    help_menus.show_createLink_help()
    sys.exit(0)

  url = sys.argv[2]

  if url.startswith('http://'):
    url = url[len('http://'):]
  if url.startswith('https://'):
    url = url[len('https://'):]

  command = f'ssh {misc.host} sudo -E python3 ~/link-deployment/run_pipeline.py --application {url} '

  if "-C" in sys.argv or "-A" in sys.argv:
    command += '-C '
  if "-S" in sys.argv:
    command += '-S '

  subprocess.run(command)
else:
  for i in range(1, len(sys.argv)):
    opt = sys.argv[i]
    if opt == "--help" or opt == "-h" or opt == "help":
      help_menus.show_spsApp_help()