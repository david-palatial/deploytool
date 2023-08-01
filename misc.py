import subprocess
import json
import re

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
        separator = version_string[1] if version_string[1] in ('.', '-') else '.'
        
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
    print(e)
    return False, None