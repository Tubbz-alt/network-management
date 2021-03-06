#!flask/bin/python

import json
from functools import partial

import httplib2
import networkx as nx
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch, OVSKernelSwitch
from mininet.topo import LinearTopo
from mininet.topolib import TreeTopo
from mininet.util import dumpNodeConnections

from flask_swagger_ui import get_swaggerui_blueprint

import os


app = Flask(__name__)
cors = CORS(app)


### swagger specific ###
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Seans-Python-Flask-REST-Boilerplate"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
### end swagger specific ###


# @app.route("/spec")
# def spec():
#     return jsonify(swagger(app))


global_net = None

gtopo_type = None
gswitch_num = None
gnodes_per_switch = None 

# open file and load the flows links from previous session if exist
gflows_list = []
glob_data = {}

with open('../flowsLog.json', 'r') as glob_file:
    try:
        glob_data = json.load(glob_file)
        gflows_list = glob_data['gflows_list']
    except ValueError:
        pass
glob_file.close()


gshortest_path = []
gstats_list = []


def create_net(controller_ip, controller_port, topo_type, switch_type, nodes_per_switch, switch_num, mac):
    """Bootstrap a Mininet network using the Minimal Topology"""

    # Create an instance of our topology
    if topo_type == 'tree':
        topology = TreeTopo(depth=switch_num, fanout=nodes_per_switch)
    else:
        topology = LinearTopo(k=switch_num, n=nodes_per_switch)

    if switch_type == 'OVSKernelSwitch':
        switch = partial(OVSKernelSwitch, protocols='OpenFlow13')
    else:
        switch = partial(OVSSwitch, protocols='OpenFlow13')

    if controller_port == 'default':
        controller = lambda name: RemoteController(name, ip=controller_ip)
    else:
        controller = lambda name: RemoteController(name, ip=controller_ip, port=int(controller_port))

    # Create a network based on the topology, using OVS and controlled by a remote controller.
    global global_net
    global_net = Mininet(topo=topology, controller=controller,
                         switch=switch, autoSetMacs=mac, waitConnected=True)


def start_net(net, ping_all=False, cli=False):
    """
    Starts the network that is passed to it.
    :param net: the network to be started
    :param ping_all: after start pingAll()
    :param cli: Drop the user in to a CLI so user can run commands.
    """
    net.start()
    dumpNodeConnections(net.hosts)
    if ping_all:
        net.pingAll()
    if cli:
        CLI(net)


@app.route('/network', methods=['POST'])
def create_network():
    # Get request data
    ip = request.json.get('ip')
    if ip == 'localhost':
        ip = '127.0.0.1'

    port = request.json.get('port')
    mac = request.json.get('mac')
    if mac == 'true':
        mac = True
    elif mac == 'false':
        mac = False

    global gtopo_type
    global gswitch_num
    global gnodes_per_switch



    topoType = request.json.get('topoType')
    gtopo_type = topoType

    switchType = request.json.get('switchType')
    switchNum = int(request.json.get('switchNum'))

    gswitch_num = switchNum

    nodesPerSwitch = int(request.json.get('nodesPerSwitch'))

    gnodes_per_switch = nodesPerSwitch

    delete_flows()

    # Create Network
    create_net(ip, port, topoType, switchType, nodesPerSwitch, switchNum, mac)
    start_net(global_net)

    create_net_dict = {
            'msg': 'Network Created',
            'topologyType': topoType
        }
    return json.dumps(create_net_dict)


    return jsonify({'msg': 'Network Created'})


def clean_up_everything():
    global gshortest_path
    global gflows_list
    global gstats_list

    for url in gflows_list:
        delete_flow(url)

    del gshortest_path[:]  # delete shortest path list
    del gflows_list[:]  # delete all urls from global list
    # Also empty json file with saved flows

    with open('../flowsLog.json', 'w') as json_file:
        try:
            file_data = {}
            file_data['gflows_list'] = []
            json.dump(file_data, json_file)
        except ValueError:
            pass
    json_file.close()

    del gstats_list[:]  # delete stats list


@app.route('/network', methods=['DELETE'])
def delete_network():

    global global_net
    if global_net is not None:

        clean_up_everything()

        global_net.stop()
        global_net = None

        return jsonify({'msg': 'Network Stopped'})
    else:
        return jsonify({'msg': 'Network Already Stopped'})


@app.route('/network', methods=['GET'])
def network_exists():
    print 'exists?'
    print global_net
    if global_net is None:
        return jsonify({'status': 'down'})
    else:
        return jsonify({'status': 'up'})


@app.route('/shortest_path', methods=['DELETE'])
def delete_shortest_path():
    global gshortest_path
    del gshortest_path[:]  # delete shortest path list
    return jsonify({'success': True})


@app.route('/shortest_path', methods=['POST'])
def find_shortest_path():
    if global_net is None:
        return jsonify({'status': 'down'})

    graph = nx.Graph()

    links_list = request.json.get('links')

    for link in links_list:
        e = (link[0], link[1])
        graph.add_edge(*e)

    nodes_list = request.json.get('nodes')

    for node in nodes_list:
        graph.add_node(node)

    node_src = request.json.get('node_source')
    node_dest = request.json.get('node_dest')
    shortest_path = nx.shortest_path(graph, node_src, node_dest)

    global gshortest_path
    gshortest_path = shortest_path  # assign shortest_path list to our global list

    return jsonify({'shortest_path': gshortest_path})


@app.route('/shortest_path', methods=['GET'])
def get_shortest_path():
    return jsonify({'shortest_path': gshortest_path})


@app.route('/flows', methods=['DELETE'])
def delete_flows():
    global gshortest_path
    global gflows_list
    global gstats_list

    clean_up_everything()

    if len(gshortest_path) == 0 and len(gflows_list) == 0 and len(gstats_list) == 0:
        return jsonify({'success': True})

    return jsonify({'success': False})


def delete_flow(url):
    response = requests.delete(url, headers={
                               'Accept': 'application/json', 'Authorization': 'Basic YWRtaW46YWRtaW4='})


@app.route('/flows', methods=['GET'])
def stat_flows():
    if len(gstats_list) is not 2:
        return jsonify({'success': False})

    return stats()


def stats():
    time_before = gstats_list[0]
    time_after = gstats_list[1]
    time_diff = time_before - time_after
    # following formula  (y2 - y1) / y1)*100,where time_before=y2 time_after=y1
    time_diff_prc = ((time_before - time_after) / time_after) * 100

    stats_dict = {
        'sourceDest': {'timeBefore': str(time_before), 'timeAfter': str(time_after), 'timeDiff': str(time_diff),
                       'timeDiffPrc': str(time_diff_prc)}, 'success': True}

    return json.dumps(stats_dict)


@app.route('/flows', methods=['POST'])
def create_flows():
    global gstats_list
    # call ping_between_hosts_and_get_avrg_time() without flows
    time_without_flows = ping_between_hosts_and_get_avrg_time()
    # store in gstats_list[0] the avrg time before setting the flows
    gstats_list.append(float(time_without_flows))

    content_json = request.get_json()
    # print 'Did I receive json format? [{}] --> Content is [{}] '.format(request.is_json, content_json)

    src_mac_address = content_json['srcMacAddress']
    dest_mac_address = content_json['destMacAddress']

    nodes_info = content_json['nodesInfo']

    for switch_info in nodes_info:
        switch_id = switch_info['switchId']  # openflow:<number>
        port_number = str(switch_info['portNumber'])
        table_id = str(switch_info['tableId'])
        flow_id = '0'

        response_from_odl = create_flow(
            switch_id, table_id, flow_id, src_mac_address, dest_mac_address, port_number)

    # Update json file for saving flows
    data = {}
    data['gflows_list'] = gflows_list
    with open('../flowsLog.json', 'w') as json_file:
        json.dump(data, json_file)
    json_file.close()

    # call ping_between_hosts_and_get_avrg_time() with the flows
    time_with_flows = ping_between_hosts_and_get_avrg_time()
    # store in gstats_list[1] the avrg time before setting the flows
    gstats_list.append(float(time_with_flows))

    return stats()


def create_flow(openflow_id, table_id, flow_id, src_mac_address, dest_mac_address, port_number):
    flow_dict = {'flow': [{
        'id': flow_id,
        'match': {'ethernet-match': {'ethernet-source': {'address': src_mac_address},
                                     'ethernet-destination': {'address': dest_mac_address},
                                     'ethernet-type': {'type': '0x800'}}},
        'instructions': {'instruction': [
            {'apply-actions': {'action': [{'output-action': {'output-node-connector': port_number}, 'order': '1'}]},
             'order': '1'}]},
        'installHw': 'false',
        'table_id': table_id}]}

    # e.g http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:1/table/2/flow/0
    h = httplib2.Http(".cache")
    h.add_credentials('admin', 'admin')

    url_to_send_to_odl = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/" + str(
        openflow_id) + "/table/" + str(table_id) + "/flow/" + str(flow_id)
    # print url_to_send_to_odl
    gflows_list.append(url_to_send_to_odl)


    resp, content = h.request(
        uri=url_to_send_to_odl,
        method='PUT',
        headers={'Content-Type': 'application/json'},
        body=json.dumps(flow_dict)
    )

  
    # send get in odl flows urls in 8181 to test thata the flows exists!
    if flow_exists():
        return jsonify({'success': True})
    return jsonify({'success': False})


def flow_exists():
    global gflows_list

    for url in gflows_list:
        response = requests.get(url, headers={'Accept': 'application/json',
                                              'Authorization': 'Basic YWRtaW46YWRtaW4='}).json()
        respons_str = str(response)

        if 'errors' in respons_str:  # it means that the flow doesnt exist
            return False

    return True  # the flow exists


@app.route('/pingall', methods=['POST'])
def pingall():
    global_net.pingAll()
    return jsonify({'success': True})


def ping_between_hosts_and_get_avrg_time():

    h_src_name = gshortest_path[0]
    h_dest_name = gshortest_path[-1]


    h_src_id, h_dest_id = "0x" + h_src_name[-2:], "0x" + h_dest_name[-2:]

    h_src_int, h_dest_int = int(h_src_id, 16), int(h_dest_id, 16)  # convert hex string to hex number

    if gtopo_type == 'tree':
        h_src_suffix  = h_src_int
        h_dest_suffix = h_dest_int

        h_src, h_dest = global_net.getNodeByName('h' + str(h_src_suffix)), global_net.getNodeByName(
            'h' + str(h_dest_suffix))  # from Mininet lib.. for more info refer to http://mininet.org/api/classmininet_1_1net_1_1Mininet.html
        # print 'Tree1 :: h_src_suffix [{}] & h_dest_suffix [{}] '.format(h_src_suffix, h_dest_suffix)

    else: #means that is a linear topology
        #pay attention naming policy is not the same as in tree topology 

        switch_src_suffix = (h_src_int -1 // gswitch_num) 
        host_src_suffix = (h_src_int -1 % gnodes_per_switch) 

        if switch_src_suffix == 0:
            switch_src_suffix =1
        if host_src_suffix ==0:
            host_src_suffix =1 

        switch_dest_suffix = (h_dest_int -1 // gswitch_num) 
        host_dest_suffix = (h_dest_int -1 % gnodes_per_switch) 

        if switch_dest_suffix == 0:
            switch_dest_suffix =1
        if host_dest_suffix ==0:
            host_dest_suffix =1 

        h_src  = global_net.getNodeByName('h' + str(host_src_suffix) + 's' + str(switch_src_suffix))
        
        h_dest = global_net.getNodeByName('h' + str(h_dest_suffix) + 's' + str(switch_dest_suffix))  


    # ping 10 times from src to dest host
    test_ping = h_src.cmd('ping -c10 %s' % h_dest.IP())
    print test_ping

    # first split
    # str from "ping statistics" and after
    avrgStats = test_ping.split("ping statistics", 1)[1]

    # second split
    # take list after spliting the str with '/' token
    split2 = avrgStats.split("/")

    avrgTime = split2[4]  # take the avrg time value

    return avrgTime


if __name__ == '__main__':
    # app.run(debug=True)
    http_server = WSGIServer(('', 5000), app)
    print "INFO: Server Started!"
    os.system("mn -c")
    http_server.serve_forever()
