
	#FROM ubuntu
	FROM adamrehn/ue4-runtime:20.04-cudagl11.1.1

	USER root
	RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub
	RUN apt-get update && apt-get -y upgrade
	RUN apt-get install -y libsecret-1-0

        #"/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_TemplateClient.sh"

        # Copy the packaged project files from the build context
        COPY --chown=ue4:ue4 . /home/ue4/project

        # Ensure the project's startup script is executable
        RUN chmod +x "/home/ue4/project/ThirdTurn_TemplateClient.sh"

	USER ue4

        # Set the project's startup script as the container's entrypoint
        ENTRYPOINT ["/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_TemplateClient.sh"]
    