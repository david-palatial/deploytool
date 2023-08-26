import sys
import subprocess
import shutil
import os
import time
import queue
import threading
import docker
import shlex
import json
import random
import string
import socket
import misc
import time
import tempfile
import paramiko
import help_menus
from datetime import datetime
import tempfile
import shutil
from dotenv import dotenv_values

exe_path = misc.get_exe_directory()
env_values = dotenv_values(os.path.join(exe_path, ".env"))
env_path = os.path.join(exe_path, ".env")
options_path = os.path.join(exe_path, "configuration", "config.json")

def generate_config_file(branch, default_config, container_tag=None, owner=None):
  config_data = misc.load_json(os.path.join(exe_path, "configuration", 'default.json'))

  config_data.update(default_config)
  
  json_data = misc.load_json(options_path)

  if owner in json_data["domains"].keys():
    if branch in json_data["domains"][owner].keys():
      config_data.update(json_data["domains"][owner][branch])
    elif "default" in json_data["domains"][owner].keys():
      config_data.update(json_data["domains"][owner]["default"])
  elif branch in json_data["applications"].keys():
    config_data.update(json_data["applications"][branch])

  tmp = tempfile.mktemp()
  with open(tmp, 'w') as f:
    json.dump(config_data, f)

  shutil.copy(tmp, f"{tmp}.copy")

  return (tmp, f"{tmp}.copy", config_data)

def switch_active_version(branch, version, path=None):
  print("Setting active version...\n")

  if not path:
    subprocess.run(f"sps-client application update --name {branch} --activeVersion {version}")
  else:
    subprocess.run(f"sps-client application update --name {branch} -f {path}")

def set_new_version(branch, version, owner=None, container_tag=None, resetting=False, path=options_path):
    existingVersions = misc.get_versions(branch)
    if existingVersions and version in existingVersions:
      switch_active_version(branch, version)
      return
      #print(f"error: version {version} already exists. can't create")
      #sys.exit(1)
    if container_tag == None:
      container_tag = f"{env_values['REPOSITORY_URL']}{branch}:{version}"
    if resetting == True:
        print("Deleting version...")
        subprocess.run(f"sps-client version delete --name {version} --application {branch}")

    print("Creating new version...")
    subprocess.check_output("timeout 2")

    default_config = {
      "name": version,
      "buildOptions": {
        "input": {
          "containerTag": container_tag
        },
        "credentials": {
          "registry": env_values['IMAGE_REGISTRY'],
          "username": env_values['REGISTRY_USERNAME'],
          "password": env_values['REGISTRY_PASSWORD']
        }
      }
    }

    tmp, temp_file, json_data = generate_config_file(branch, default_config, container_tag, owner=owner)

    command = f'sps-client version create -a {branch} --name {version} -f {temp_file}'
    count = 1
    data = misc.get_sps_json_output(command)

    while data["statusCode"] != 200 and count != 3:
      if data["statusCode"] == 422:
        print("error: " + data["message"])
        sys.exit(1)
      print("Retrying...")
      subprocess.check_output("timeout 2")
      data = misc.get_sps_json_output(command)
      count += 1

    if data["statusCode"] == 200:
      print(json.dumps(data, indent=7))
    else:
      print("error: " + data["response"])
      sys.exit(1)

    json_data.update({
      "name": branch,
      "activeVersion": version
    })

    tmp2, temp_file_2, _ = generate_config_file(branch, json_data, container_tag=container_tag, owner=owner)
    switch_active_version(branch, version, path=temp_file_2)

    os.remove(tmp)
    os.remove(tmp2)
    os.remove(temp_file)
    os.remove(temp_file_2)

def reset_app_version(branch, path=options_path, owner=None):
    exists, data = misc.try_get_application(branch)
    if exists:
      if data['response']['activeVersion']:
        version = data['response']['activeVersion']
        set_new_version(branch, version, resetting=True, path=path, owner=owner)

def make_new_application(branch, version, tag=None, wait=True, owner=None):
    sys.stdout.write("Creating application")
    if wait == True:
      print_dots(25)
    else:
      print_dots(3)
    subprocess.run(f"sps-client application create --name {branch}")
    set_new_version(branch, version, container_tag=tag, owner=owner)

def reset_application(branch, version=None, container_tag=None, owner=None):
  exists, data = misc.try_get_application(branch)

  if not exists:
    print(f"error: app '{branch}' does not exist.")
    sys.exit(1)

  if not "activeVersion" in data["response"]:
    print(f"error: app '{branch}' has no set version. can't reset")
    sys.exit(1)

  activeVersion = data["response"]["activeVersion"]
  if not version:
    version = activeVersion

  # If an image tag is not supplied we look for the active version info to do a reset
  if not container_tag:
    versions = data["response"]["versions"]
    for v in range(0, len(versions)):
      if versions[v]["name"] == activeVersion:
        container_tag = versions[v]["buildOptions"]["input"]["containerTag"]
        break

  print(f"Delete {branch}...")
  subprocess.run(f"sps-client application delete --name {branch}")

  make_new_application(branch, version, tag=container_tag, owner=owner, wait=False)

  sys.stdout.write("Finishing up")
  print_dots(6)
  print("FINISHED")

def print_dots(duration):
    q = queue.Queue()

    def print_dots_thread():
        end_time = time.time() + duration
        while time.time() < end_time:
            q.put(". ")
            time.sleep(1)
        q.put(None)  # Signal end of dots

    thread = threading.Thread(target=print_dots_thread)
    thread.start()

    while True:
        item = q.get()
        if item is None:
            break
        print(item, end="")
        sys.stdout.flush()


def build_docker_image(branch, image_tag):
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
        registry=env_values['IMAGE_REGISTRY'],
    )

    Dockerfile = f"""
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

    with open("../Dockerfile", "w") as f:
        f.write(Dockerfile)
    
    os.system(f"docker build -t {env_values['REGISTRY_USERNAME']}/{image_tag} ..")
    os.system(f"docker push {env_values['REGISTRY_USERNAME']}/{image_tag}")

def starts_with_single_hyphen(s):
    return s.startswith('-') and not s.startswith('--')


def deploy(argv):
    branch = None
    build = None
    app_only = False
    server_only = False
    use_firebase = False
    image_only = False
    version = None
    self_selected_version = False
    owner = None

    global options_path

    options = [
        "-h",
        "--help",
        "-A",
        "-b",
        "--branch",
        "-h",
        "--help",
        "-S",
        "-C",
        "-I",
        "-F",
        "--vn",
        "--image-only",
        "--server-only",
        "--app-only",
        "--client-only",
        "--config",
        "--avm",
        "--add-volume-mount",
        "--firebase",
        "--version-name",
        "--owner"
    ]

    single_options = ["-F", "-A", "-C", "-I", "-S"]

    reset_version = False
    #argv = argv.split()

    if len(argv) < 1:
        help_menus.show_Deploy_help()
        sys.exit(1)

    dir_name = os.path.abspath(argv[0])

    for i in range(0, len(argv)):
      if starts_with_single_hyphen(argv[i]):
        for j in range(1, len(argv[i])):
          opt = argv[i][j]
          match opt:
            case 'A':
              app_only = True
            case 'C':
              app_only = True
            case 'S':
              server_only = True
            case 'I':
              image_only = True
            case 'F':
              use_firebase = True

    if app_only and image_only:
      image_only = False

    for i in range(0, len(argv)):
        opt = argv[i]
        if opt.startswith("--") and opt not in options:
            print(f"Invalid option {opt}")
            help_menus.show_Deploy_help()
            sys.exit(1)
        if opt == "--help" or opt == "-h":
            help_menus.show_Deploy_help()
            sys.exit(0)
        if opt == "--branch" or opt == "-b":
            if i + 1 >= len(argv):
                print(f"error: {opt} provided without an argument")
                print(f"Example: sps-app deploy 22-11-23_build-A-CD {opt} dev")
                sys.exit(1)
            branch = argv[i + 1]
        if opt == "--app-only" or opt == "--client-only":
            app_only = True
        if opt == "--server-only":
            server_only = True
        if opt == "--image-only":
            image_only = True
            app_only = True
        if opt == "--owner":
          if i + 1 >= len(argv):
            print("error: --owner provided without an argument")
            sys.exit(1)
          owner = argv[i+1]
        if opt == "--vn" or opt == "--version-name":
            if i + 1 >= len(argv):
              print(f"error: {opt} provided without an argument")
              print(f"Example: sps-app deploy . -b test {opt} testVersion")
              sys.exit(1)
            version = argv[i + 1].lower().replace('_', '-').replace('.', '-')
            self_selected_version = True
        if opt == "--config":
            if i + 1 >= len(argv):
                print("error: --config provided without a path")
                sys.exit(1)
            options_path = argv[i + 1]
            reset_version = True
        if opt == "--add-volume-mount":
            options_path = persistent_volume_path
            reset_version = True
        if opt == "--firebase":
            use_firebase = True

    if not os.path.exists(dir_name):
        print(f"error: directory {dir_name} does not exist.")
        sys.exit(1)

    if app_only and not os.path.exists(os.path.join(dir_name, "LinuxClient")) and not os.path.exists(os.path.join(dir_name, "Linux")):
        print(f"error: directory Linux or LinuxClient does not exist in {dir_name}")
        sys.exit(1)

    if server_only and not os.path.exists(os.path.join(dir_name, "LinuxServer")):
        print(f"error: directory LinuxServer does not exist in {dir_name}")
        sys.exit(1)

    if branch == None:
        branch = misc.generate_random_string()

    branch = branch.replace('_', '-').replace('.', '-').lower()

    os.chdir(dir_name)

    if not server_only:
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxClient")) and not os.path.exists(os.path.join(os.getcwd(), "Linux")):
            print(f"error: directory Linux or LinuxClient does not exist in {os.path.abspath(os.getcwd())}")
            sys.exit(1)

        if os.path.exists(os.path.join(os.getcwd(), "Linux")):
          os.chdir("Linux")
        elif os.path.exists(os.path.join(os.getcwd(), "LinuxClient")):
          os.chdir("LinuxClient")

        if not self_selected_version:
          highestVersion = misc.get_highest_version(misc.get_versions(branch))
          if highestVersion == None:
            version = "v0-0-1"
          else:
            version = misc.increment_version(highestVersion)

        image_tag = f"{branch}:{version}"

        if use_firebase:
            build_docker_image(branch, image_tag)
        else:
            opt = ""
            
            if os.path.exists(os.path.join(".temp", "result.json")):
              opt = "--skip-building"
            subprocess.run(f'image-builder create --package . --tag {env_values["REPOSITORY_URL"]}{image_tag} {opt}')
            sys.exit(0)

        if image_only:
          print("FINISHED")
          sys.exit(0)

        exists, data = misc.try_get_application(branch)
        # Set a new version if this version doesn't already exist
        if exists:
            print(f'making version: {version}')
            set_new_version(branch, version, resetting=reset_version, path=os.path.join("..", options_path), owner=owner)
        else:
            make_new_application(branch, version, wait=False, owner=owner)
            if app_only:
              sys.stdout.write("Finishing up")
              print_dots(6)

        appInfo = {
          "customDockerBuild": use_firebase,
          "uploader": { "sourceDirectory": os.path.dirname(dir_name) }
        }

        misc.save_version_info(branch, appInfo, client=True)
        os.chdir("..")

    if not app_only:
        if not server_only:
          print("\n")
        
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxServer")):
            print(f"error: directory LinuxServer does not exist in {os.path.abspath(os.getcwd())}")
            sys.exit(1)

        print("Checking for service file...")
        exists = misc.file_exists_on_remote(misc.host, f'/etc/systemd/system/server_{branch}.service')

        if exists:
          print("Stopping running server...")
          subprocess.run(f'ssh -v {misc.host} "sudo systemctl stop server_{branch}.service"', stdout=subprocess.PIPE)

        print("Making directory...")        
        subprocess.run(f'ssh -v {misc.host} mkdir -p ~/servers/{branch}/LinuxServer', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        print("\nUploading server...")
        subprocess.run(f'scp -r LinuxServer/* {misc.host}:~/servers/{branch}/LinuxServer/', shell=True, text=True, capture_output=False)

        print("\nUpload complete\n")

        if exists:
          print("Starting server...")
          subprocess.run(f'ssh -v {misc.host} "sudo systemctl start server_{branch}.service"', stdout=subprocess.PIPE)

        data = {
          "dedicatedServerLocation": f"/home/david/servers/{branch}/"
        }

        misc.save_version_info(branch, data, client=False)

    print("FINISHED")
