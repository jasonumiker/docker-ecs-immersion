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
1. Run `cd docker-ecs-immersion` then `git submodule update --init --recursive` to bring in the submodules.

## Introduction to Docker

1. Run `docker version` to confirm that both the client and server are there and working (in this case on the same EC2 Instance running our Cloud9)

### Example of running stock nginx from Docker Hub

1. Run `docker run -d -p 8080:80 --name nginx nginx:latest` to run nginx in the background as a daemon as well as map port 8080 on our host to 80 in the container
    1. The -d is to run it as a daemon (in the background), the -p maps the host port 8080 to 80 in the container, --name gives us a name we can run further docker commands against easily and then the image repository and tag we want to run.
    1. Run `docker ps` to see our container running
    1. Click on the `Preview` menu in the middle of the top bar then choose `Preview running application`. This opens a proxied browser tab on the right to show what is running on localhost port 8080 on our Cloud9 EC2 instance. Click the `Pop Out Into New Window` icon in the upper right-hand corner of that right pane to give it its own tab then close the preview tab.
    1. Run `docker logs nginx --follow` to tail the logs the container is sending to STDOUT (including its access logs)
    1. Refresh the preview in the separate browser tab a few times and then come back to see the new log line entries
        1. **NOTE** For some reason refreshing this within Cloud9 sometimes doesn't leave these log lines - do it in the separate tab within your browser
    1. Press Ctrl-C to exit the log tailing
    1. Run `docker exec -it nginx /bin/bash` to open a shell *within* our container (-it means interactive)
    1. Run `cd /usr/share/nginx/html` then `cat index.html` to see the content the nginx is serving which is part of the container.
    1. Run `echo "Test" > index.html` and then refresh the browser preview tab to see the content change
        1. If we wanted to commit this change to the image as a new layer we could do it with a `docker commit` - otherwise it'll stay in this container but be reverted if you go back to the image.
    1. Run `exit` to exit our interactive shell
1. Run `docker stop nginx` to stop our container
1. Run `docker ps -a` (-a means all including the stopped containers) to see that our container is still there but stopped. At this point it could be restarted with a `docker start nginx` if we wanted.
1. Run `docker rm nginx` to remove the stopped container from our machine then another `docker ps -a` to confirm it is now gone
1. Run `docker images` to see that the nginx:latest image is there there cached
1. Run `docker rmi nginx:latest` to remove the nginx image from our machine's local cache

### Now let's customise nginx with our own content - nyancat
1. Run `cd ~/environment/docker-ecs-immersion/aws-cdk-nyan-cat/nyan-cat`
1. Run `cat Dockerfile` - this is start from the upstream nginx:alpine image (alpine is a slimmer base image option offered by nginx and many other base images) and then copy the contents of this path into /usr/share/nginx/html in our container replacing the default page it ships with
1. Run `docker build -t nyancat .` to build an image called nyancat:latest from that Dockerfile
1. Run `docker history nyancat:latest` to see all of the commands and layers that make up the image - see our new layer?
1. Run `docker run --rm -d -p 8080:80 --name nyancat nyancat:latest` (--rm means to delete the container once it is stopped rather than leave it around to be restarted) 
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
1. Click `Actions` -> `Security` -> `Modify IAM Role` then choose `EC2FullAdmin` and click `Save`
1. Go to the Cloud9 tab and click on the gear in the upper right hand corner
1. In the Preferences tab go to AWS Settings on the left then turn off AWS Managed Temporary credentials
1. Close the Preferences tab


Then go back to the Terminal tab in our Cloud9 and:
1. Run `aws configure set default.region ap-southeast-2` to set our default region to Sydney
1. Run `curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-linux && chmod +x copilot && sudo mv copilot /usr/local/bin/copilot` to install Copilot
1. Run `cd ~/environment/docker-ecs-immersion`
1. First we'll create our [application](https://aws.github.io/copilot-cli/docs/concepts/applications/) by running `copilot app init`
    1. Enter `nyancat` as the name of our application
1. Then we'll create our [environment](https://aws.github.io/copilot-cli/docs/concepts/environments/) by running `copilot env init`
    1. Enter 'dev' as the name of the environment
    1. Use the down arrow to select `[profile default]` for the credentials and press Enter. This will use the default credentials of the IAM Role assigned to our EC2 instance.
    1. Press Enter to select `Yes, use default.` for the network and press Enter. We could instead customise the CIDRs or choose and existing VPCs/subnets if we wanted here but for our workshop we'll let it create a new network with its default settings.
1. Next, we'll create or [service](https://aws.github.io/copilot-cli/docs/concepts/services/) by running `copilot svc init`
    1. Use the down arrows to select `Load Balanced Web Service` and press Enter.
    1. Enter `www` for the name
    1. Use the down arrow twice to select `Enter custom path for your Dockerfile` and press Enter
    1. Enter `/home/ec2-user/environment/docker-ecs-immersion/aws-cdk-nyan-cat/nyan-cat/Dockerfile` for the path
    1. Press Enter to select the default port of 80
    1. This actually just generated a manifest file that we can use to deploy. Have a look at it with `cat copilot/www/manifest.yml`. The schema available to you to customise this service is documented at https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/
1. Finally, we'll deploy our new service to our new environment by running `copilot svc deploy --name www --env dev`. This will:
    1. Build the container locally with a `docker build`
    1. Push it to the Elastic Container Registry (ECR)
    1. Deploy it as a Service (which scales/heals ECS Tasks similar to an Auto Scaling Group on EC2) on ECS Fargate behind an ALB
    1. Output the URL to the new ALB you can go to in your browser to see our nyancat container running on the Internet!

This was all actually done via CloudFormation and you can go to the CloudFormation service in the AWS Console and see separate stacks for the application, for the environment and for the service. If you go into those you can see the Templates that copilot generated and deployed for you. If you choose not not use copilot then you can be inspired by these Templates to make your own to manage ECS directly.

TODO: Give them a tour around the ECS and EC2 service consoles all the things that were provisioned (ECS Cluster/Service/Tasks, ALB, etc.)

### AWS Copilot CI/CD Pipeline

Rather than building our container on the machine that we run copilot CLI from (our laptop etc.), [copilot can set up a CI/CD pipeline in the cloud based on AWS CodePipeline/CodeBuild for us too](https://aws.github.io/copilot-cli/docs/concepts/pipelines/).

1. Run `copilot pipeline init`
1. Press Enter to accept the `dev` environment default
1. Press Enter to accept the repository
1. Note the `buildspec.yml` and `pipeline.yml` files that it generated - have a look at them.
1. (Don't actually run this) If you were to run `copilot pipeline update` it would deploy that pipeline for you from those files - but you'd have to administrative permissions to the git repo to both pull it as well as create the webhook(s) to trigger the builds whenever you merge. Rather than walk you through creating a GitHub account and doing it take our word for it.

[(Optional) Demo this for the attendees if they'd like to see it]

### AWS Cloud Development Kit (CDK)

The AWS Cloud Development Kit as we discussed also generates CloudFormation for you. But while copilot is focused and opinionated to keep things simple, CDK is a more general tool that can allow you to do literally anything that you can do in AWS however you'd like it done.

However, we have added [higher-level constructs](https://docs.aws.amazon.com/cdk/api/latest/docs/aws-ecs-patterns-readme.html) that build on the foundational constructs/classes of the CDK to get closer to the simplicity of copilot when it comes to many areas like ECS too.

1. Run `cd ~/environment/docker-ecs-immersion/aws-cdk-nyan-cat/cdk`
1. Run `cat lib/cdk-stack.ts`
1. Note that there is one line to create the VPC (and this automatically will create a 'proper' VPC with public and private subnets and NAT gateways etc.), one to create the ECS Cluster and then a a construct called `ApplicationLoadBalancedFargateService`. That construct will:
    1. Build the container locally on the machine we're running the CDK on
    1. Create an ECR Repository and push it to that
    1. Create an ALB
    1. Create an ECS Fargate Task Definition
    1. And create and ECS Service to run/scale/heal that and manage its ALB Target Group for us.
1. Run `nvm install --lts` to install the LTS version of node.js needed to run the CDK
1. Run `sudo npm install --upgrade -g aws-cdk` to install the CDK via npm
1. Run `npm upgrade` to update the package.json to the latest available package versions
1. Run `npm install` to install the packages needed from npm
1. Run `cdk synth` to generate the CloudFormation template from our CDK template
1. Note that this is the CloudFormation that the few lines of CDK we cat-ed above has turned into.
1. Run `cdk bootstrap` to create an S3 artifact bucket CDK needs
1. Deploy that with a `cdk deploy` to build our container locally, generate the CloudFormation template as above (as well upload it to the artifact bucket) and then call the AWS APIs to deploy that CloudFormation template. As part of that the local cdk CLI will also push the local image it (re)builds up to the new ECR it creates as part of that process as well.
1. Answer `y` to the security confirmation and press Enter (it will show you any IAM and Security Group/firewall changes that will happen if you proceed)

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
1. Click `Actions` -> `Security` -> `Modify IAM Role` then choose `EC2FullAdmin` and click `Save`
1. Click the `Connect` button then choose the `RDP client` tab then click the `Download remote desktop file` button and then click `Get password`
1. Browse to the certificate file you just downloaded and click `Decrypt Password`
1. Copy the Password that has been revealed to your clipboard and then open the .RDP file you downloaded to log into the Windows Bastion

Use Windows Docker locally on the instance:
1. Open PowerShell
1. Run `docker version` to see that Docker for Windows is built-in to this AMI and ready to go
1. Run `docker run --rm -d --name iis -p 8080:80 mcr.microsoft.com/windows/servercore/iis` to run stock IIS
1. Note how huge the image is and how long it takes it to both download and extract - 1/2 of Windows needs to be within the Windows container images and this makes them slow to pull/start/scale/heal compared to Linux
1. Open Internet Explorer and Go to `http://localhost:8080`. You will see the default IIS site
1. Run `docker stop iis` to stop the container

 Now lets launch the nyancat content:
1. In PowerShell
1. Run `Invoke-WebRequest -uri "https://github.com/jasonumiker/docker-ecs-immersion/raw/main/nyancat-windows.zip" -Method "GET"  -Outfile nyancat-windows.zip`
1. Unzip the files. Run `Expand-Archive -Path nyancat-windows.zip -DestinationPath C:\nyancat-windows`
1. Run `cd c:\nyancat-windows`
1. Run `cat Dockerfile` and see how Dockerfiles on Windows are similar but you use Powershell instead of the unix shell
1. Run `docker build -t nyancat-windows .` to delete the default site and put our nyancat in its place
1. Note how since we had already download the IIS base layers we are building on they were cached really speeding things up
1. Run `docker run --rm -d --name nyancat-windows -p 8080:80 nyancat-windows` to run our nycat on Windows via IIS
1. Go to `http://localhost:8080` in IE and see it running
1. Run `docker stop nyancat-windows` to stop the container

Push our new nyancat-windows image to ECR:
1. Install the AWS CLI by running `msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi` in Powershell
1. Restart Powershell so the AWS CLI is now in the PATH
1. Run `cd c:\nyancat-windows`
1. Go to the AWS Console and go to the Elastic Container Registry (Amazon ECR)
1. Click the orange `Get Started` button
1. Type `nyancat-windows` for the repository name then click `Create repository`
1. Enter the repository then click the `View push commands` button in the top right of the scree
1. Select the Windows Tab
1. Copy the first command and paste into PowerShell in your RDP session. This will log in
1. Copy and paste the third command to re-tag our image (we already did the build in step 2)
1. Copy and paste the fourth command to push the image

### Windows ECS Example

Now we'll take our nyancat container and run it on ECS

Go back to your terminal in Cloud9 and:
1. Run `nvm install --lts` to switch back to the lts version we installed above (since it is already installed this should be quick)
1. Run `cd ~/environment/docker-ecs-immersion/windows`
1. Run `pip install -r requirements.txt` to install the necessary python packages from pip.
1. Run `cdk deploy`
1. Go to the ALB address output at the end of the deployment to see our nyancat hosted by IIS on Windows via ECS

## ECS Anywhere

In order to run ECS Anywhere you need a machine with systemd and Docker. This could be anything from bare metal on a raspberry pi to a VM to even Docker-in-Docker.

The easiest way to test this is using Docker-in-Docker on the Cloud9 that we've already been using Docker on.

The Dockerfile in the ecsanywhere folder will build an Amazon Linux 2 container that has both systemd and docker that can serve as an ECS Anywhere sandbox for us.

On the Cloud9:
1. We need to free some disk space before proceeding as the Cloud9 only has 10GB - there are a number of unneeded docker images pre-loaded on the Cloud9 that we can clean to do that. Run `docker rmi -f $(docker images -a -q)` which will remove all the locally cached images.
1. `cd ~/environment/docker-ecs-immersion/ecsanywhere`
1. `docker build -t ecsanywhere-dind .`
1. `docker run -d --privileged --name ecsanywhere -p 8080-8090:8080-8090 ecsanywhere-dind:latest`
1. `docker exec -it ecsanywhere /bin/bash`

We'll paste the command to join this to Systems manager and ECS into that interactive shell within the container in a moment.

Then in the AWS Console:
1. Go to the ECS Service
1. Click the blue `Create Cluster` button
1. Choose Networking only (should already be selected by default) and click the blue `Next step` button
1. Type `ECSAnywhere` for the Cluster name, click the box to enable CloudWatch Container Insights, and then click the blue `Create` button
1. Click the blue `View Cluster` button
1. Go to the ECS Instances tab in the middle of hhe console
1. Click the `Register External Instances` button
1. Click the blue `Next step` button
1. Click the blue `Copy` button to copy the command we need to the clipboard

Then just paste that command in to the interactive shell within our ecsanywhere-dind container to register this container against both SSM and ECS Anywhere.

Once you have started the container you can do a `docker stop ecsanywhere` to pause it and `docker start ecsanywhere` to start it up again when you need - it'll retain the ECS cluster membership until you do a `docker rm` and remove the container from your system.

To remove it from both SSM and ECS Anywhere go to the Fleet Manager in the SMS service and deregister it there.

But we'll leave it up and running for now to show deploying a Task to it.

### Deploying nyancat to our ECS Anywhere

We already had pushed our Linux nyancat image twice - one with copilot and once with CDK. So we'll use that image. But we'll create a new Task Definition and Service manually in the console and to deploy it to our ECS Anywhere Docker-in-Docker environment.

First we'll find the image URI in the ECR console:
1. Go to the ECR service in the AWS Console
1. Click on the blue name/link for `nyancat/www`
1. Click on the squares to the left of the URI for `nyancat-www` to copy the URI path to the right of the squares - or highlight the path and copy it yourself.

Then we'll deploy it to ECS Anywhere:
1. Go to the ECS Service in the AWS Console
1. Go to Task Definitions on the Left Hand pane
1. Click on the blue `Create new Task Definition` button
1. Choose `EXTERNAL` and then click the `Next step` button
1. Enter `nyancat-external` for the Task Definition Name
1. Choose `nyancat-dev-www-TaskRole` for the Task Role dropdown
1. Choose `nyancat-dev-www-ExecutionRole` for the Task execution role
1. Click the blue `Add container` button
1. Paste in the ECR URI from above
1. Enter a hard limit of 1024
1. Enter 8080 for Host port and 80 for Container port in Port Mappings
1. Click the Add button the bottom of the Add container pane
1. Click the Create button on the bottom right
1. Click the JSON tab - we could have written this ourselves or used CDK to generate it but the console can help us click around with what we want and it'll generate it for us too.
1. Click on the `Actions` button and then choose `Create Service`
1. Pick EXTERNAL for the `Launch type`
1. Pick the `ECSAnywhere` cluster from the dropdown
1. Enter `nyancat-external` for the `Service name`
1. Enter 1 for the number of tasks
1. Click the blue `Next step` button at the bottom
1. Click the `Review and create` button
1. Click the `Create Service` button
1. Click the `View Service` button
1. Once the Task has successfully started you should be able to see it on http://localhost:8080 from within Cloud9
