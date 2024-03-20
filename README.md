> **_NOTE_**: Many changes were made to have this application run in a container,
> it does not support local runs without changes.

# StarlingX ChatBot demo

The purpose of this demo is to demonstrate a chatbot that is capable of make
API requests to the Kubernetes cluster inside the StarlingX system. In order to
provide the informations to the user about the StarlingX cluster, the chatbot
uses the Open AI LLM and LangChain framework.

The specific case scenario of this demonstration is to show the ChatBot
retrieving information about the pod `busybox` that is facing a deployment error.
Furthermore the chatbot will also need to provide possible solutions for the
problem.

## Requisits

Before starting the execution of the chatbot some steps needs to be done in
order to the chatbot function in its full intention.

First you will need to install the required python libraries, we recommend the
creation of a virtual enviromment.

```shell
git clone https://github.com/Danmcaires/poc_GenAI.git
cd poc_GenAI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir certs
```

After installing the required libraries, start your StarlingX VM. While you
virtual machine is starting up, you will need to create a port-forward so the
chatbot can access the kubernetes cluster via API. If you are using VirtualBox,
to create the port-forward use this command:

```shell
VBoxManage natnetwork modify --netname "NAT_NAME" --port-forward-4 kubernetes:tcp:[]:6443:GUEST_IP:6443"
```

Note that this command assumes that your virtual machine is using a NatNetwork.
Make sure to change `ǸAT_NAME` for the name of you NatNetwork and `GUEST_IP`
for your StarlingX OAM IP.

Because the kubernetes API is in a internal network and its certificates are
pointing to this network you will need make an iptable in your host so any
request made to the kuberenetes IP is rerouted to your localhost (from now on
this README will assume that your VM is using a NatNetwork, if this is not the
case make sure to do the necessary adjustments). For creating the iptable,
execute the following command:

```shell
sudo iptables -t nat -A OUTPUT -d 192.168.206.1 -j DNAT --to-destination 127.0.0.1
```

Unless you determined otherwise during your StarlingX deployment. the IP address
that your StarlingX Kubernetes cluster will be, is `192.168.206.1`, that is the
`cluster_host_subnet` network.

Now that your virtual machine has already booted, log in to it so you can make
the necessary configurations before starting your chatbot.

Once inside your StarlingX system, you will need to add an IP route from the
`cluster_host_subnet` to your `external_oam_floating_address`.To do this, simply
run:

```shell
sudo ip route add 192.168.206.0/24 via OAM_IP
```

For the chatbot be able to access the Kubernetes cluster inside your StarlingX
system, it will need a few certificates and key. The chatbot assumes that this
files are in a folder named `certs/` inside the chatbot directory. For exporting
the files to your host machine run the following commands:

```shell
sudo scp /etc/kubernetes/pki/ca.crt <hostname>@<hostIP>:/home/<hostname>/poc_GenAI/certs/
sudo scp /etc/kubernetes/pki/apiserver-kubelet-client.crt <hostname>@<hostIP>:/home/<hostname>/poc_GenAI/certs/
sudo scp /etc/kubernetes/pki/apiserver-kubelet-client.key <hostname>@<hostIP>:/home/<hostname>/poc_GenAI/certs/
```

Make the necessary substitutions in your host address.

Finally, you will need a valid OpenAI API Key in order to run the chatbot. To
get one visit the [OpenAI website](https://platform.openai.com/docs/overview).
Since OpenAI API is not free, you may need to pay before using the API key.

## Running the chatbot

Now that you made all the necessary configuration, to execute the chatbot run:

```shell
cd $HOME/poc_GenAI
source venv/bin/activate
python3 main.py
```
