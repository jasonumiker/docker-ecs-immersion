from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    core
)
import os

class ECSWindowsStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new VPC
        vpc = ec2.Vpc(self, "Vpc",
            max_azs=2
        )

        ## ECS Cluster
        cluster = ecs.Cluster(
            self, "Cluster",
            vpc = vpc
        )

        # Add Windows Capacity/Instances to the cluster to run on containers on
        capacity = cluster.add_capacity(
            "WindowsCapacity",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.LARGE),
            machine_image=ecs.EcsOptimizedImage.windows(ecs.WindowsOptimizedVersion.SERVER_2019),
            min_capacity=1,
            max_capacity=2,
            can_containers_access_instance_role=False
        )

        # Deploy nyancat-windows
        # Get the container from our nycat-windows ECR repository
        repository=ecr.Repository.from_repository_name(
            self, "ECRRepository",
            repository_name="nyancat-windows"
        )    
        
        # Create the Task Definition
        taskdef = ecs.Ec2TaskDefinition(
            self, "TaskDefinition",
            # The only supported network mode on Windows Instances atm is NAT
            network_mode=ecs.NetworkMode.NAT   
        )
        taskdef.add_container(
            "nyancat-windows",
            image=ecs.ContainerImage.from_ecr_repository(repository=repository,tag="latest"),
            # By specifying a host_port of 0 we are telling it pick a random one in the dynamic range for us
            port_mappings=[ecs.PortMapping(container_port=80, host_port=0)],
            # Note that you have to specify a CPU and memory limit for Windows ECS to work properly 
            memory_limit_mib=1024,
            cpu=1024
        )

        # Create the ECS Service
        service = ecs.Ec2Service(
            self, "Service",
            task_definition=taskdef,
            cluster=cluster,
            # It can take quite ahwile for the 5-6GB image to pull and the container to start so setting a high grace period (10 minutes)
            health_check_grace_period=core.Duration.minutes(10)
        )

        # Create the ALB
        lb = elbv2.ApplicationLoadBalancer(
            self, "ALB",
            vpc=vpc,
            internet_facing=True
        )
        listener=lb.add_listener("PublicListener", port=80, open=True)
        health_check=elbv2.HealthCheck(
            interval=core.Duration.seconds(60),
            path="/",
            timeout=core.Duration.seconds(5)
        )
        listener.add_targets(
            "ECS",
            port=80,
            targets=[service],
            health_check=health_check
        )
        # Output our ALB's address in the CloudFormation Stack's Outputs
        core.CfnOutput(
            self, "LoadBalancerDNS",
            value=lb.load_balancer_dns_name
        )

app = core.App()
ecs_windows_stack = ECSWindowsStack(app, "ECSWindowsStack")
app.synth()