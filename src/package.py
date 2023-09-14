import subprocess

name = "test"
subprocess.run(f'ssh david@prophet.palatialxr.com mkdir -p ~/deployment/builds/{name} ~/servers/{name}', shell=True)
subprocess.run(f'scp -r .LinuxClient ./LinuxServer david@prophet.palatialxr.com:~/deployment/builds/{name}', shell=True)
subprocess.run(f'ssh david@prophet.palatialxr.com ./deployment/run_pipeline.sh {name}', shell=True)