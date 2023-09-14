from datetime import datetime
import socket
import os
import subprocess
import json
import requests
import re
import string
import random
import docker
import tempfile
import shutil
import sys
import time
from dotenv import dotenv_values

def get_exe_directory():
  if getattr(sys, 'frozen', False):  # Check if the script is running as a frozen executable
    # When running as a frozen executable, sys.executable points to the executable file itself
    exe_path = os.path.dirname(sys.executable)
  else:
    # When running as a script, use the path of the script
    exe_path = os.path.abspath(__file__)

  # Get the directory of the executable
  exe_directory = os.path.dirname(os.path.dirname(exe_path))
  return exe_directory

exe_path = get_exe_directory()
env_values = dotenv_values(os.path.join(exe_path, ".env"))
host = env_values['HOST']

def file_exists_on_remote(host, remote_file_path):
    try:
        # SSH command to check if the file exists
        command = f'ssh -v {host} test -f {remote_file_path} && echo True || echo False'

        # Run the command and suppress the output
        result = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE)

        output = result.stdout.strip()
        exists = True if output == 'True' else False

        # If the command returns without raising an exception, the file exists
        return exists

    except subprocess.CalledProcessError:
        # If the command returns a non-zero exit code, the file does not exist
        return False
    except Exception as ex:
        print(f"Error: {str(ex)}")
        return False

def increment_version(version_string):
    # Define a regular expression pattern to match the version format
    pattern = r'^v(\d)[.-](\d)[.-](\d)$'
    
    # Check if the input string matches the pattern
    match = re.match(pattern, version_string)
    if match:
        # Extract the individual version components as integers
        major, minor, patch = map(int, match.groups())
        
        # Increment the patch component by one
        patch += 1
        
        # Check for overflow and adjust the other components if necessary
        if patch > 9:
            patch = 0
            minor += 1
            if minor > 9:
                minor = 0
                major += 1
        
        # Determine the original separator (dot or hyphen) from the input version string
        separator = version_string[2] if version_string[2] in ('.', '-') else '.'
        
        # Return the updated version string with the original separator
        return f"v{major}{separator}{minor}{separator}{patch}"
    else:
        # If the input string doesn't match the pattern, return version_string
        return version_string

def load_json(file_path):
  with open(file_path, "r") as f:
    json_data = f.read()
  return json.loads(json_data)

def load_json_content(file_path):
  with open(file_path, "r") as f:
     content = f.read()

  return json.loads(content)

def get_sps_json_output(command):
  output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  json_data = output.stdout
    
  if output.stderr:
    prefix = "Error: "
    json_data = output.stderr[len(prefix):]

  json_data = json_data.decode('utf-8')

  return json.loads(json_data)

def try_get_application(name):
  command = f"sps-client application read --name {name}"
  try:
    output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    json_data = output.stdout
    
    if output.stderr:
      prefix = "Error: "
      json_data = output.stderr[len(prefix):]

    json_data = json_data.decode('utf-8')

    data = json.loads(json_data)

    return data["statusCode"] == 200, data
  except subprocess.CalledProcessError as e:
    return False, None

def get_public_ip():
    response = requests.get("https://api.ipify.org?format=json")
    if response.status_code == 200:
        data = response.json()
        return data['ip']
    else:
        return None

def is_valid_version(version_str):
    return bool(re.match(r'^v\d+\.\d+\.\d+$|^v\d+-\d+-\d+$', version_str))

def version_key(version_str):
    return tuple(map(int, version_str[1:].replace('-', '.').split('.')))

def get_highest_version(versions_list):
    if not versions_list:
      return None
    valid_versions = [version for version in versions_list if is_valid_version(version)]
    if not valid_versions:
        return None

    highest_version = max(valid_versions, key=version_key)
    return highest_version


def get_version_objects(application):
  exists, data = try_get_application(application)
  if not exists or not 'versions' in data['response']:
    return []

  ret = []
  versions = data["response"]["versions"]
  for v in range(0, len(versions)):
    ret.append(versions[v])

  return ret

def get_versions(application):
  ret = []
  versions = get_version_objects(application)
  for v in range(0, len(versions)):
    ret.append(versions[v]["name"])

  return ret

def generate_random_string():
    letters = string.ascii_letters
    digits = string.digits

    first_char = random.choice(letters)

    rest_chars = random.choices(letters + digits, k=8)

    random_string = ''.join([first_char] + rest_chars)
    random_string = ''.join(random.sample(random_string, len(random_string)))

    return random_string

def check_docker_image_exists(image_name):
    try:
        client = docker.from_env()
        # Check if the image exists locally
        client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        try:
            # If the image is not available locally, attempt to pull it from Docker Hub
            client.images.pull(image_name)
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as e:
            print(f"Error occurred while pulling the image: {e}")
            return False
    except docker.errors.APIError as e:
        print(f"Error occurred while checking image existence: {e}")
        return False

def write_to_remote(file_path, data):
  tmp = tempfile.mktemp()
  with open(tmp, 'w') as f:
    f.write(data)

  shutil.copy(tmp, f"{tmp}.copy")

  base_filename = os.path.basename(tmp)

  subprocess.run('scp {}.copy {}:~/.tmp/'.format(tmp, host), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run('ssh {} "cat ~/.tmp/{}.copy | sudo tee {}"'.format(host, base_filename, file_path), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def build_docker_image(branch, image_tag, dockerfile_path, is_client=True):
    # Get the current working directory
    current_directory = os.getcwd()

    # Extract the name of the current directory from the path
    directory_name = os.path.basename(current_directory)

    # Check if the directory name is "Linux" (case-sensitive)
    if directory_name == "Linux":
        folder_type = ""
    else:
        folder_type = "Client"

    # Add dependencies if image tag does not exist

    client = None
    try:
        client = docker.from_env()
        client.ping()
    except docker.errors.DockerException:
        print("error: Docker Desktop is not running.")
        sys.exit(1)

    client.login(
        username=env_values['REGISTRY_USERNAME'],
        password=env_values['REGISTRY_PASSWORD'],
        registry=env_values['IMAGE_REGISTRY_API'],
    )

    ClientDockerfile = f"""
FROM adamrehn/ue4-runtime:20.04-cudagl11.1.1

# Install our additional packages
USER root

RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub
RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
        libsecret-1-0 \
        libgtk2.0-0:i386 \
        libsm6:i386

USER ue4

# Copy the packaged project files from the build context
COPY --chown=ue4:ue4 "./Linux{folder_type}" /home/ue4/project

# Ensure the project's startup script is executable
RUN chmod +x "/home/ue4/project/ThirdTurn_Template{folder_type}.sh"

RUN ln -s /usr/lib/x86_64-linux-gnu/libsecret-1.so.0 /home/ue4/project/Palatial_V01_UE51/Binaries/Linux/libsecret-1.so.0
RUN ls -al /home/ue4/project/

# Set the project's startup script as the container's entrypoint
ENTRYPOINT ["/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_Template{folder_type}.sh"]
    """

    ServerDockerfile = """
FROM ubuntu:latest

WORKDIR /

RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt     apt-get update && apt-get -y upgrade &&     apt-get install -y --no-install-recommends         libsecret-1-0

COPY ./LinuxServer /LinuxServer

RUN chmod +x "/LinuxServer/ThirdTurn_TemplateServer.sh"

ENTRYPOINT ["bash", "/LinuxServer/ThirdTurn_TemplateServer.sh"]
"""

    with open(os.path.join(dockerfile_path, "Dockerfile"), "w") as f:
        f.write(ClientDockerfile if is_client else ServerDockerfile)

    os.system(f'docker build -t {env_values["REPOSITORY_URL"]}/{image_tag} "{dockerfile_path}"')
    os.system(f"docker tag {env_values['REPOSITORY_URL']}/{image_tag} {env_values['REPOSITORY_URL']}/{branch}:latest")
    os.system(f"docker push {env_values['REPOSITORY_URL']}/{image_tag}")
    os.system(f"docker push {env_values['REPOSITORY_URL']}/{branch}:latest")

    os.remove(os.path.join(dockerfile_path, "Dockerfile"))

def save_version_info(branch, data={}, client=True):
  print("Saving version info...")
  current_datetime = datetime.now()
  date = current_datetime.strftime("%Y%m%d_%H_%M_%S")
  dir_name = os.path.basename(os.getcwd())

  appExists, jsonData = try_get_application(branch)
  version = dir_name
  timeCreated = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
  timeLastUpdated = timeCreated

  if appExists:
    version = jsonData["response"].get("activeVersion")
    if not version:
      version = dir_name
    else:
      versions = jsonData["response"]["versions"]
      for i in range(0, len(versions)):
        if versions[i]["name"] == version:
          timeCreated = versions[i]["timeCreated"]
          timeLastUpdated = versions[i]["timeLastUpdated"]

  if client:
    subprocess.run(f'ssh -v {host} sudo mkdir -p /var/log/cw-app-logs/{branch}/client', stdout=subprocess.PIPE)
    versionInfoAddress = f'/var/log/cw-app-logs/{branch}/client/{version}_{current_datetime.strftime("%Y%m%d-%H_%M_%S")}.log'
    activeVersionAddress = f'/var/log/cw-app-logs/{branch}/client/activeVersion.log'
  else:
    subprocess.run(f'ssh -v {host} sudo mkdir -p /var/log/cw-app-logs/{branch}/server', stdout=subprocess.PIPE)
    versionInfoAddress = f'/var/log/cw-app-logs/{branch}/server/{version}_{date}.log'
    activeVersionAddress = f'/var/log/cw-app-logs/{branch}/server/activeVersion.log'

  if version == dir_name:
    image_tag = f'server-{branch}:{current_datetime.strftime("%Y%m%d-%H_%M_%S")}'
  else:
    image_tag = f'server-{branch}:{version}'

  #print("Building and pushing dedicated server docker image:")
  #build_docker_image(f"server-{branch}", image_tag, os.getcwd(), is_client=False)

  info = {
    "branch": branch,
    "version": version,
    "versionLogLocation": versionInfoAddress,
    "timeCreated": timeCreated,
    "timeLastUpdated": timeLastUpdated,
    "uploader": {
      "hostName": socket.gethostname(),
      "ipAddress": str(get_public_ip()),
      "sourceDirectory": dir_name,
      "command": ' '.join(sys.argv)
    }
  }

  data.update(info)

  json_data = json.dumps(data, indent=2)

  tmp = tempfile.mktemp()
  with open(tmp, 'w') as f:
    f.write(json_data)

  shutil.copy(tmp, f"{tmp}.copy")

  base_filename = os.path.basename(tmp)

  subprocess.run('scp {}.copy {}:~/.tmp/'.format(tmp, host), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run('ssh -v {} "cat ~/.tmp/{}.copy | sudo tee {}"'.format(host, base_filename, versionInfoAddress), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run('ssh -v {} "cat ~/.tmp/{}.copy | sudo tee {}"'.format(host, base_filename, activeVersionAddress), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  os.remove(tmp)
  os.remove(f"{tmp}.copy")

  print("\nVersion information saved to " + versionInfoAddress)

def wait_for_status(app, status, msg=None):
  count = 0
  while True:
    data = get_sps_json_output(f'sps-client application info -n {app}')
    
    if count % 2 == 0 and data["statusCode"] == 200 and re.search(data["response"]["status"], status):
      break
    else:
      if count == 20:
        break
      if msg:
        print(msg, end="")
      sys.stdout.flush()
      time.sleep(1)

def wait_for_deleted(app, msg=None):
  count = 0
  while True:
    data = get_sps_json_output(f'sps-client application info -n {app}')
    
    if count % 2 == 0 and data["statusCode"] == 404:
      break
    else:
      if count == 20:
        break
      if msg:
        print(msg, end="")
      sys.stdout.flush()
      time.sleep(1)

      count += 1
  