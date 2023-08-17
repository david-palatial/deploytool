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

host = 'david@palatial.tenant-palatial-platform.coreweave.cloud'

def file_exists_on_remote(host, remote_file_path):
    try:
        # SSH command to check if the file exists
        command = f'ssh {host} test -f {remote_file_path} && echo True || echo False'

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

def get_versions(application):
  exists, data = try_get_application(application)
  if not exists or not 'versions' in data['response']:
    return None

  ret = []
  versions = data["response"]["versions"]
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
      versions = get_versions(branch)
      if versions:
        for i in range(0, len(versions)):
          if versions[i]["name"] == version:
            timeCreated = versions[i]["timeCreated"]
            timeLastUpdated = versions[i]["timeLastUpdated"]

  if client:
    subprocess.run(f'ssh {host} sudo mkdir -p /usr/local/bin/cw-app-logs/{branch}/client', stdout=subprocess.PIPE)
    versionInfoAddress = f'/usr/local/bin/cw-app-logs/{branch}/client/{version}_{current_datetime.strftime("%Y%m%d-%H_%M_%S")}.log'
    activeVersionAddress = f'/usr/local/bin/cw-app-logs/{branch}/client/activeVersion.log'
  else:
    subprocess.run(f'ssh {host} sudo mkdir -p /usr/local/bin/cw-app-logs/{branch}/server')
    versionInfoAddress = f'/usr/local/bin/cw-app-logs/{branch}/server/{version}_{date}.log'
    activeVersionAddress = f'/usr/local/bin/cw-app-logs/{branch}/server/activeVersion.log'

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

  subprocess.run('scp {}.copy {}:~/.tmp/'.format(tmp, host), shell=True, stdout=subprocess.PIPE)
  subprocess.run('ssh {} "cat ~/.tmp/{}.copy | sudo tee {}"'.format(host, base_filename, versionInfoAddress), shell=True, stdout=subprocess.PIPE)
  subprocess.run('ssh {} "cat ~/.tmp/{}.copy | sudo tee {}"'.format(host, base_filename, activeVersionAddress), shell=True, stdout=subprocess.PIPE)

  os.remove(tmp)
  os.remove(f"{tmp}.copy")

  print("Version information saved to " + versionInfoAddress)
  