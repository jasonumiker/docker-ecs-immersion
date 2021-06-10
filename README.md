# Docker and ECS Immersion Day

## Working Environment

### Cloud9
We'll start by setting up a Cloud9 which is an EC2 instance accessible via a browser-based IDE and Terminal. Being backed by a dedicated Linux machine, containers run right on these Cloud9 instances when you use the docker commands.

1. Sign into the AWS Console for the provided account
1. Choose the Sydney region in the upper right dropdown
1. Click the `Create environment` button
1. Name your environment `cloud9` and click the `Next step` button
1. Change the instance type to `m5.large` then click the `Next step` button accepting the other defaults
1. Click the `Create environment` button
1. When it comes up close everything (the two bottom tabs as well as the bottom pane that has two more tabs in it)
1. Then open a new terminal by choosing the `Window` menu then picking `New Terminal`
1. Run `git clone https://github.com/jasonumiker/docker-ecs-immersion.git`
1. Run `git submodule update --init --recursive` to bring in the submodules.

## Introduction to Docker

1. Run `docker version` to confirm that both the client and server are there and working (in this case on the same EC2 Instance running our Cloud9)

### Example of running stock nginx from Docker Hub

1. Run `docker run -d -p 8080:80 --name nginx nginx:latest` to run nginx in the background as a daemon as well as map port 8080 on our host to 80 in the container
    1. Run `docker ps` to see our container running
    1. Click on the `Preview` menu in the middle of the top bar then choose `Preview running application`. This opens a proxied browser tab on the right to show what is running on localhost port 8080 on our Cloud9 EC2 instance. Click the `Pop Out Into New Window` icon in the upper right hand corner of that right pane to give it its own tab then close the preview tab.
    1. Run `docker logs nginx --follow` to tail the logs the container is sending to STDOUT (including its access logs)
    1. Refresh the preview in the separate browser tab a few times and then come back to see the new log line entries
        1. **NOTE** For some reason refreshing this within Cloud9 sometimes doesn't leave these log lines - do it in the separate tab within your browser
    1. Press Ctrl-C to exit the log tailing
    1. Run `docker exec -it nginx /bin/bash` to open a shell *within* our container
    1. Run `cd /usr/share/nginx/html` then `cat index.html` to see the content the nginx is serving which is part of the container.
    1. Run `echo "Test" > index.html` and then refresh the browser preview tab to see the content change
        1. If we wanted to commit this change to the image as a new layer we could do it with a `docker commit` - otherwise it'll stay in this container but be reverted if you go back to the image.
    1. Run `exit` to exit our interactive shell
1. Run `docker stop nginx` to stop our container
1. Run `docker ps -a` to see that our container is still there but stopped. At this point it could be restarted with a `docker start nginx` if we wanted.
1. Run `docker rm nginx` to remove the stopped container from our machine then another `docker ps -a` to confirm it is now gone
1. Run `docker images` to see that the nginx:latest image is there there cached
1. Run `docker rmi nginx:latest` to remove the nginx image from our machine's local cache

### Now let's customise nginx with our own content - nyancat
1. Run `cd ~/environment/docker-ecs-immersion/aws-cdk-nyan-cat/nyan-cat`
1. Run `cat Dockerfile` - this is start from the upstream nginx:alpine image (alpine is a slimmer base image option offered by nginx and many other base images) and then copy the contents of this path into /usr/share/nginx/html in our container replacing the default page it ships with
1. Run `docker build -t nyancat .` to build an image called nyancat:latest from that Dockerfile
1. Run `docker history nginx:latest` to see all of the commands and layers that make up the image - see our new layer?
1. Run `docker run --rm -d -p 8080:80 --name nyancat nyancat:latest` 
1. Click on the `Preview` menu in the middle of the top bar then choose `Preview running application`. This opens a proxied browser tab on the right to show what is running on localhost port 8080 on our Cloud9 EC2 instance. Click the `Pop Out Into New Window` icon in the upper right hand corner of that right pane to give it its own tab then close the preview tab.
    1. See our new content that is built into the image for nginx to serve?
1. Run `docker stop nyancat` to stop and clean up that container (we said --rm so Docker will automatically clean it up when it stops)

### Compiling your app within the docker build

Getting a local development environment with the 'right' versions of things like the JDK and associated tooling can be complicated. With docker we can have the docker build do the build but also do it in another build stage and then only copy the artifacts across we need at runtime to our runtime container image with multi-stage docker builds.

This example is Spring Boot's (a common Enterprise Java Framework) Docker demo/example. But it could apply to any compiled language.

1. Run `cd ~/environment/docker-ecs-immersion/top-spring-boot-docker/demo`
1. Run `cat Dockerfile` and see our two stages - the first running a Maven install and the second taking only the JAR and putting it in a runtime container image as we don't need all those build artifacts at runtime keeping the runtime image lean.
1. Run `docker build -t spring .` to do the build. This will take awhile for it to pull Spring Boot down from Maven etc. We don't have the JDK or tools installed on our Cloud9 but are compiling a Java app. If different apps needed different version of the JDK or tools you could easily build them all on the same machine this way too.
1. Once that is complete re-run the `docker build -t spring .` command a 2nd time. See how much faster it goes once it has cached everything locally?
1. Run `docker run --rm -d -p 8080:8080 --name spring spring` to run our container.
1. Run `curl http://localhost:8080` - it just returns Hello World (and Spring Boot is a very heavy framework to just do that! We wanted to see how you'd do a heavy Enterprise Java app though)
1. Run `docker stop spring`

## Introduction to ECS

Now that we containerised our nyancat content together with an nginx to serve it let's deploy that to ECS

We'll do this two ways - first with [AWS Copilot](https://aws.github.io/copilot-cli/) and then with the [AWS Cloud Development Kit (CDK)](https://docs.aws.amazon.com/cdk/api/latest/docs/aws-ecs-patterns-readme.html). These both actually generate CloudFormation for you but Copilot is more simple and opinionated while CDK is a general purpose tool that can do nearly anything but is more complex.

### AWS Copilot

First we'll need to give AWS Administrator Access to our Cloud9 Instance:
1. Go to the IAM service in the AWS Console
1. Go to `Roles` on the left-hand navigation pane
1. Click the blue `Create role` button
1. Choose `EC2` under `Common use cases` in the middle of the page then click the `Next: Permissions` button in the lower right
1. Tick the box next to `AdministratorAccess` then click the `Next: Tags` button in the lower right
1. Click the `Next: Review` button in the lower right
1. Enter `EC2FullAdmin` foe the `Role name` and then click `Create role`
1. Go to the `Instances` section of the EC2 service in the AWS Console
1. Tick the box to the left of our cloud9 instance
1. Click `Actions` -> `Security` -> `Modify IAM Role` then choose `ECSFullAdmin` and click `Save`

Then go back to the Terminal in our Cloud9 and:
1. Run `aws configure set default.region ap-southeast-2` to set our default region to Sydney
1. Run `curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-linux && chmod +x copilot && sudo mv copilot /usr/local/bin/copilot` to install Copilot
1. Run `cd ~/environment/docker-ecs-immersion`
1. First we'll create our [application](https://aws.github.io/copilot-cli/docs/concepts/applications/) by running `copilot app init`
    1. Enter `nyancat` as the name of our application
1. Then we'll create our [environment](https://aws.github.io/copilot-cli/docs/concepts/environments/) by running `copilot env init`
    1. Enter 'dev' as the name of the environment
    1. Use the arrows to select `[profile default]` for the credentials and press Enter. This will use the default credentials of the IAM Role assigned to our EC2 instance.
    1. Use the arrows to select `Yes, use default.` for the network and press Enter. We could instead customise the CIDRs or choose and existing VPCs/subnets if we wanted here but for our workshop we'll let it create a new network with its default settings.
1. Next, we'll create or [service]() by running `copilot svc init`
    1. Use the arrows to select `Load Balanced Web Service` and press Enter.
    1. Enter `www` for the name
    1. Use the arrows to select `Enter custom path for your Dockerfile` and press Enter
    1. Enter `/home/ec2-user/environment/aws-cdk-nyan-cat/nyan-cat/Dockerfile` for the path
    1. Press Enter to select the default port of 80
    1. This actually just generated a manifest file that we can use to deploy. Have a look at it - `copilot/www/manifest.yml`. The schema available to you to customise this service is documented at https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/
1. Finally, we'll deploy our new service to our new environment by running `copilot svc deploy --name www --env dev`. This will:
    1. Build the container locally with a `docker build`
    1. Push it to the Elastic Container Registry (ECR)
    1. Deploy the service to ECS Fargate behind an ALB
1. That step will output the URL to the new ALB you can go to in your browser to see our nyancat container running on the Internet!

This was all actually done via CloudFormation and you can go to the CloudFormation service in the AWS Console and see separate stacks for the application, for the environment and for the service. If you go into those you can see the Templates that copilot generated and deployed for you. If you choose not not use copilot then you can be inspired by these Templates to make your own to manage ECS directly.

TODO: Give them a tour around the ECS and EC2 consoles all the things that were provisioned (ECS Cluster/Service/Tasks, ALB, etc.)

### AWS Copilot CI/CD Pipeline

TODO: Show them how copilot can provision a pipeline to build/deploy as well

### AWS Cloud Development Kit (CDK)

TODO: CDK Example

## Windows Containers

### Local Windows Example

First we'll show how to build an IIS container to host nyancat on Windows instead of our nginx container we used on Linux as well as the local Docker experience on Windows. We'll spin up a Windows bastion host to test this on - but the Docker experience should be similar to that on your Windows laptop/desktop.

Create and log into a Windows EC2 Instance:
1. Go to the EC2 Service in the AWS Console
1. Go to `Instances` on the navigation pane on the left side
1. Click the orange `Launch instances` button in the upper right
1. In the search box type `container` and press Enter then click the blue `Select` button next to `Microsoft Windows Server 2019 Base with Containers
1. Choose the `t3.large` instance type in the list and once that is selected click the `Review and Launch` button
1. Click the `Launch button` then `Create a new key pair` from the dropdown then enter the name `workshop-windows-bastion` and click `Download Key Pair`
1. Then click the blue `Launch Instances` button
1. Go back to the EC2 Instances view and tick the new instance there to select it
1. Click `Actions` -> `Security` -> `Modify IAM Role` then choose `ECSFullAdmin` and click `Save`
1. Click the `Connect` button then choose the `RDP client` tab then click the `Download remote desktop file` button and then click `Get password`
1. Browse to the certificate file you just downloaded and click `Decrypt Password`
1. Copy the Password that has been revealed to your clipboard and then open the .RDP file you downloaded to log into the Windows Bastion

Use Windows Docker locally on the instance:
1. Run `docker version` to see that Docker for Windows is built-in to this AMI and ready to go
1. Run `docker run --rm -d --name iis -p 8080:80 mcr.microsoft.com/windows/servercore/iis` to run stock IIS
1. Note how huge the image is and how long it takes it to both download and extract - 1/2 of Windows needs to be within the Windows container images and this makes them slow to pull/start/scale/heal compared to Linux
1. Go to `http://localhost:8080` in IE and see the default IIS site
1. Run `docker stop iis` to stop the container
TODO: Add instructions for getting nyancat on the machine (.zip in the git repo they can download from github?)
1. Run `cd c:\aws-cdk-nyan-cat`
1. Run `cat Dockerfile` and see how Dockerfiles on Windows are similar but you use Powershell instead of the unix shell
1. Run `docker build -t nyancat-windows .` to delete the default site and put our nyancat in its place
1. Note how since we had already download the IIS base layers we are building on they were cached really speeding things up
1. Run `docker run --rm -d --name nyancat-windows -p 8080:80 nyancat-windows` to run our nycat on Windows via IIS
1. Go to `http://localhost:8080` in IE and see it running
1. Run `docker stop nyancat-windows` to stop the container

Push our new nyancat-windows image to ECR:
1. Install the AWS CLI by running `msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi` in Powershell
1. Restart Powershell so the AWS CLI is now in the PATH
1. Go to the ECR service in the AWS Console
1. Click the orange `Create repository` button
1. Type `nyancat-windows` for the repository name then click `Create repository`
1. Enter the repository then click the `View push commands` button
1. Copy and paste the first command to log in
1. Copy and paste the third command to re-tag our image (we already did the build in step 2)
1. Copy and paste the fourth command to push the image

### Windows ECS Example

Now we'll take our nyancat container and run it on ECS

TODO instructions on deploying the Windows CDK

## ECS Anywhere

### Demo of deploying to my Linux laptop

TODO: Linux Laptop example

### Workshop of deploying to EC2 (pretending it is not in the AWS region)

(Stretch goal) TODO: Workshop for attendees