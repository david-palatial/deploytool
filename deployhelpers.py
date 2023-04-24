import sys
import subprocess
import os
import time
import queue
import threading
import docker
import json

def does_image_tag_exist(client, image, tag):
    try:
        client.images.get(f"{image}:{tag}")
        return True
    except docker.errors.ImageNotFound:
        return False

def switch_active_version(branch, version):
  sys.stdout.write("Setting active version...\n")
  subprocess.run(f"sps-client application update --name {branch} --activeVersion {version}")

def set_new_version(branch, version):
  container_tag = f'docker.io/dgodfrey206/{branch}:{version}'
  sys.stdout.write("Creating new version...")
  subprocess.check_output("timeout 2")
  subprocess.run(f"sps-client version create --application {branch} --name {version} --buildOptions.input.containerTag {container_tag} --buildOptions.credentials.registry \"https://index.docker.io/v1/\"")
  switch_active_version(branch, version)

def make_new_application(branch, version, step=1):
  sys.stdout.write("Creating application")
  if step != 1:
    print_dots(25)
  subprocess.run(f"sps-client application create --name {branch}")
  set_new_version(branch, version)


def reset_application(branch, image_tag=None):
  cmd = f'sps-client application read --name "{branch}"'
  output = subprocess.check_output(cmd, shell=True)

  # Parse the JSON data into a Python dictionary
  data = json.loads(output)

  activeVersion = data['response']['activeVersion']

  if image_tag == None:
    image_tag = f"{branch}:{activeVersion}"

  container_tag = f"docker.io/dgodfrey206/{image_tag}"

  step = 1
  print("Delete {branch}")

  subprocess.run(f"sps-client application delete --name {branch}")
  make_new_application(branch, image_tag.split(':')[1], step + 1)

  sys.stdout.write("Finishing up")
  print_dots(18)
  print(f"\n\n{branch} reset: https://{branch}.palatialxr.com")



def show_help():
    print(
        "usage: deploy <dir> [-b or --branch] <branch> [options...]\n\
-A, --app-only     Only deploy the client\n\
-b, --branch       The application branch to deploy to (dev, demo, prophet, etc.)\n\
-h, --help         Get help for commands\n\
-S, --server-only  Only deploy the server\n"
    )
    print("Example: deploy 22-11-23_build-A-CD --branch dev")

def print_periodic(interval):
    while True:
        sys.stdout.write('. ')
        sys.stdout.flush()
        time.sleep(interval)

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


def deploy(argv):
    branch = None
    build = None
    app_only = False
    server_only = False

    options = [
        "-h",
        "--help",
        "-A",
        "-b",
        "--branch",
        "-h",
        "--help",
        "-S",
        "--server-only",
    ]

    argv = argv.split()

    if len(argv) < 1:
        show_help()
        sys.exit(1)

    dir_name = os.path.abspath(argv[0])

    for i in range(1, len(argv)):
        opt = argv[i]
        if opt[0] == "-" and opt not in options:
            print(f"Invalid option {opt}")
            show_help()
            sys.exit(1)
        if opt == "--help" or opt == "-h":
            show_help()
            sys.exit(0)
        if opt == "--branch" or opt == "-b":
            if i + 1 >= len(argv):
                print("error: --branch provided without an argument")
                sys.exit(1)
            branch = argv[i + 1]
        if opt == "-A" or opt == "--app-only":
            app_only = True
        if opt == "-S" or opt == "--server-only":
            server_only = True

    if not os.path.exists(dir_name):
        print(f"Directory {dir_name} does not exist.")
        sys.exit(1)

    if app_only and not os.path.exists(os.path.join(dir_name, "LinuxClient")):
        print("error: file LinuxClient does not exist".format(dir_name))
        sys.exit(1)

    if server_only and not os.path.exists(os.path.join(dir_name, "LinuxServer")):
        print("error: file LinuxServer does not exist in {}".format(dir_name))
        sys.exit(1)

    if branch == None:
        print("error: -b or --branch is required (one of dev, prophet, demo, etc..)")
        print("Example: deploy 22-11-23_build-A-CD --branch dev")
        sys.exit(1)

    image_tag = f"{branch}:{os.path.basename(dir_name)}"

    os.chdir(dir_name)
    dir_name = os.path.basename(dir_name)

    if not server_only:
        os.chdir("LinuxClient")

        # Define the base image
        base_image = "adamrehn/ue4-runtime:20.04-cudagl11.1.1"

        # Define the Dockerfile contents
        dockerfile_dep = f"""
        FROM {base_image}

        USER root

        # Import NVIDIA GPG key
        RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub

        # Update packages
        RUN apt-get update 

        # Install libsecret
        RUN apt-get install -y libsecret-1-0
        """

        dockerfile_sps = f"""
        FROM {base_image}

        # Copy the packaged project files from the build context
        COPY --chown=ue4:ue4 . /home/ue4/project

        # Ensure the project's startup script is executable
        RUN chmod +x "/home/ue4/project/ThirdTurn_TemplateClient.sh"

        # Set the project's startup script as the container's entrypoint
        ENTRYPOINT ["/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_TemplateClient.sh"]
	"""

        # Add dependencies if image tag does not exist
        client = docker.from_env()
        if not does_image_tag_exist(client, branch, dir_name):
            # Write the Dockerfile to a file
            with open("Dockerfile", "w") as f:
                f.write(dockerfile_dep)
            os.system(f"docker build -t {image_tag} .")

        with open("Dockerfile", "w") as f:
            f.write(dockerfile_sps)

        os.system(f"docker build -t {image_tag} .")
        os.system(f"docker tag {image_tag} dgodfrey206/{image_tag}")
        os.system(f"docker push dgodfrey206/{image_tag}")

        cmd = f'sps-client application info --name "{branch}"'
        output = subprocess.check_output(cmd, shell=True)

        data = json.loads(output)

        version = image_tag.split(':')[1]

        # Set a new version if this version doesn't already exist
        if data['statusCode'] == 200 and not data['response']['activeVersion'] or data['response']['activeVersion']['name'] != version:
            set_new_version(branch, version)
        else:
            make_new_application(branch, version)
        os.chdir("..")

    if not app_only:
        print("Uploading server...")
        subprocess.run(
            f'ssh david@prophet.palatialxr.com "sudo systemctl stop server_{branch}.service"'
        )
        subprocess.check_output(
            "scp -r LinuxServer david@prophet.palatialxr.com:~/servers/" + branch
        )
        subprocess.run(
            f'ssh david@prophet.palatialxr.com "sudo systemctl start server_{branch}.service"'
        )
        subprocess.run(
            f'ssh david@prophet.palatialxr.com "echo \"{dir_name}\" >> ~/servers/{branch}/version.log"'
        )

    print("FINISHED")
