import subprocess
import json
import requests
import re
import string
import random

host = 'david@new-0878.tenant-palatial-platform.coreweave.cloud'

def file_exists_on_remote(host, remote_file_path):
    try:
        # SSH command to check if the file exists
        command = f'ssh {host} test -f {remote_file_path} && echo "True" || echo "False"'

        # Run the command and suppress the output
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

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
    output = subprocess.check_output(command, shell=True, stderr=subprocess.PIPE)

    data = json.loads(output.decode())

    return True, data
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
  if not exists:
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