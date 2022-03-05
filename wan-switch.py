import socket
from pyroute2 import IPRoute
from ipaddress import ip_address, ip_network, IPv4Address
from flask import Flask, request, escape

CONFIG = {
    'wan': {
        # table: table name
           0: "5G",
        1337: "Unicom"
    },
    'priority_base': 8000,
    'lan': '192.168.51.0/24',
    'host': '192.168.51.1',
    'port': 80
}

app = Flask("wan-switch")

def init_config():
    assert(ip_network(CONFIG['lan']).version == 4,"LAN should be ipv4")
    CONFIG['lan'] = ip_network(CONFIG['lan'])
    assert(type(CONFIG['priority_base']) == int,"priority_base should be int")
    assert(type(CONFIG['wan']) == map,"WAN should be map")
    for table_id,table_name in CONFIG['wan'].items():
        assert(type(table_id) == int, "table_id should be int")
        assert(type(table_name) == str, "table_name shoule be str")

def get_wan_table_by_ip(ip:IPv4Address):
    ipr_result = IPRoute().get_rules(family=socket.AF_INET,FRA_SRC=ip.compressed)
    if len(ipr_result) == 0:
        return 0
    else:
        for rule in ipr_result:
            attrs = rule['attrs']
            for attr in attrs:
                if attr[0] == 'FRA_TABLE':
                    return attr[1]
        return 0

def gen_priority(ip:IPv4Address):
    return CONFIG["priority_base"] + int(ip) - int(CONFIG["lan"].network_address)

def set_wan_table(ip:IPv4Address,table:int):
    if ip in CONFIG["lan"] and table in CONFIG['wan'].keys():
        try:
            IPRoute().rule("delete",priority=gen_priority(ip))
        except:
            pass
        if table == 0:
            return 0
        IPRoute().rule("add",table=table,src=ip.compressed,priority=gen_priority(ip))
        return 0
    else:
        return -1 # Permission check failed

@app.route("/",methods=["GET","POST"])
def show_status():
    user_ip = ip_address(request.remote_addr)
    if user_ip in CONFIG['lan']:
        if request.method == 'POST':
            table_id = int(request.form.get("table_id"))
            set_wan_table(user_ip,table_id)
            print(user_ip,table_id)
        user_table = get_wan_table_by_ip(user_ip)
        out_buf  = "<h1>Wan switch</h1>\n";
        out_buf += "Your IP is {}<br>".format(escape(user_ip.compressed))
        out_buf += "<form method=\"POST\">"
        for table_id, table_name in CONFIG['wan'].items():
            out_buf += "<input type=\"radio\" name=\"table_id\" id=\"table_id\" value=\"{}\" {}>{}</input> <br>\n".format(table_id,"checked" if table_id == user_table else "",escape(table_name))
        out_buf += "<input type=\"submit\"></form>"
        return out_buf
    else:
        return "403 Forbidden", 403

if __name__ == "__main__":
    init_config()
    app.run(host=CONFIG['host'],port=CONFIG['port'])