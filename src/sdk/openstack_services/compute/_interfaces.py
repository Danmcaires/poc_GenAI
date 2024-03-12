import logging
from openstack.connection import Connection


LOG = logging.getLogger("openstacksdk")


class ServerInterfaces:
    def __init__(self, conn: Connection):
        self.sdk_conn = conn

    
    def list(self, server_id):
        if not server_id:
            raise AttributeError("Required attribute 'server_id' was not defined")

        LOG.debug(f"Trying to fetch server '{server_id}' interfaces")
        return self.sdk_conn.compute.server_interfaces(server_id)


    def show(self, server_id, interface_id):
        if not server_id:
            raise AttributeError("Required attribute 'server_id' was not defined")        

        if not interface_id:
            raise AttributeError("Required attribute 'interface_id' was not defined")

        LOG.debug(f"Trying to find server '{server_id}' '{interface_id}' interface")
        return self.sdk_conn.compute.get_server_interface(server_id, interface_id)
