# AWS EC2 Setup (Amazon Linux 2)

## Install pyenv

### Install Dependencies

pyenv builds Python versions from source and therefore requires all the necessary build dependencies.

```sh
sudo yum -y install openssl openssl11-devel xz-devel git-core gcc-c++ patch readline readline-devel zlib zlib-devel libyaml-devel libffi-devel make bzip2 bzip2-devel autoconf automake libtool bison sqlite sqlite-devel gnupg2
```

### Install Git

You'll need `git` installed to be able to clone the repositories

```sh
sudo yum install git
```

### Clone the pyenv Git Repository

```sh
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
```

### Configure your '.bash_profile' file

```shell
echo ' ' >> ~/.bash_profile
echo '# pyenv Configuration' >> ~/.bash_profile
echo 'export pYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'export PATH="$pYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
```

### Reinitialise your Shell

```sh
source ~/.bash_profile
```

### Testing pyenv

```sh
pyenv
```

### Install Python

```sh
pyenv install 3.11.10
```

### Configure Global Python Version

```sh
pyenv global 3.11.10
```

Check that the versions are associated correctly

```sh
pyenv versions
```

### Upgrade Pip

```sh
pip install --upgrade pip
```

## Install Tailscale

### Install the Yum repository manager:

```sh
sudo yum -y install yum-utils
```

### Add the Tailscale repository and install Tailscale:

```sh
sudo yum-config-manager --add-repo https://pkgs.tailscale.com/stable/amazon-linux/2/tailscale.repo
sudo yum -y install tailscale
```

### Use systemctl to enable and start the service:

```sh
sudo systemctl enable --now tailscaled
```

### Connect your machine to your Tailscale network and authenticate in your browser:

```sh
sudo tailscale up
```

### You're connected! You can find your Tailscale IPv4 address by running:

```sh
tailscale ip -4
```
