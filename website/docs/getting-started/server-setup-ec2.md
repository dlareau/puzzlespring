## EC2 Setup Guide

PuzzleSpring can be deployed on Amazon EC2 instances for production environments. This guide covers the basic steps to set up PuzzleSpring on an EC2 instance.

### Prerequisites

- An AWS account with EC2 access
- Basic familiarity with AWS services
- A domain name (optional, but recommended)

### Step 1: Launch an EC2 Instance

1. Log in to the AWS Management Console and navigate to EC2
2. Click "Launch Instance"
3. Choose an Amazon Machine Image (AMI)
   - Recommended: Amazon Linux 2 or Ubuntu Server LTS
4. Select an instance type
   - Recommended minimum: t3.small (2 vCPU, 2 GB RAM)
   - For larger hunts: t3.medium or larger
5. Configure instance details
   - Use default VPC and subnet settings for simplicity
   - Enable auto-assign public IP
6. Add storage
   - Minimum 20 GB for the root volume
7. Configure security groups
   - Allow SSH (port 22)
   - Allow HTTP (port 80)
   - Allow HTTPS (port 443)
8. Review and launch with your key pair

### Step 2: Connect to Your Instance

```bash
ssh -i /path/to/your-key.pem ec2-user@your-instance-public-dns
```

### Step 3: Install Docker and Docker Compose

For Amazon Linux 2:
```bash
# Update system packages
sudo yum update -y

# Install Docker
sudo amazon-linux-extras install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and log back in for group changes to take effect
exit
```

For Ubuntu:
```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Docker
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Log out and log back in for group changes to take effect
exit
```

### Step 4: Set Up Domain and SSL (Optional)

1. Point your domain to your EC2 instance's public IP
2. The built-in Caddy server will automatically obtain SSL certificates

### Step 5: Deploy PuzzleSpring

```bash
# Clone the repository
git clone https://github.com/puzzlespring/puzzlespring.git
cd puzzlespring

# Configure environment variables
cp sample.env .env
nano .env  # Edit with your settings

# Set production values in .env
# DOMAIN=your-domain.com
# DJANGO_SECRET_KEY=your-secure-key
# DB_PASSWORD=your-secure-password
# DJANGO_ENABLE_DEBUG=False
# ENABLE_REDIS_CACHE=True

# Start the application
docker-compose up -d
```

### Step 6: Initial Setup

```bash
# Run the initial setup
docker-compose exec app python manage.py initial_setup
```

### Additional Considerations

- For larger hunts, consider scaling up your EC2 instance
- Use an Elastic IP to maintain a consistent public IP address
