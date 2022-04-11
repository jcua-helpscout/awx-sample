#!/usr/bin/env python

import argparse
import json
import os
import requests
import sys

from requests.auth import HTTPDigestAuth

from rich import print as rprint

KEY_GROUPS = ['mongoDBVersion', 'providerSettings_diskIOPS']

class AtlasInventory(object):

    def __init__(self):
        self.read_cli_args()
        self.inventory = self.atlas_inventory()
        if self.args.graph:
            self.inventory = self.atlas_graph()

        # print(json.dumps(self.inventory))


    def add_key_groups(self, data):
        for host in data['_meta']['hostvars']:
            for key_group in KEY_GROUPS:
                if '_' in key_group:
                    parent_key, child_key = key_group.split('_')
                    label = 'tag_%s_%s' % (
                        key_group, data['_meta']['hostvars'][host][parent_key][child_key]
                    )
                else:
                    label = 'tag_%s_%s' % (key_group, data['_meta']['hostvars'][host][key_group])

                if data.get(label):
                    data[label].append(host)
                else:
                    new = { label: [host] }
                    data.update(new)

        rprint(data)
        return data


    def atlas_inventory(self):
        auth = HTTPDigestAuth(
            os.getenv('MONGODB_ATLAS_PUBLIC_KEY'),
            os.getenv('MONGODB_ATLAS_PRIVATE_KEY')
        )

        url = 'https://cloud.mongodb.com/api/atlas/v1.0'
        cluster = '/groups/%s/clusters' % (os.getenv('GROUP_ID'))
        result = requests.get('%s%s' % (url, cluster), auth=auth)
        data = {
            'group': {
                'hosts': [ i['name'] for i in result.json()['results'] ],
            },
            '_meta': {
                'hostvars': { i['name']:i for i in result.json()['results'] }
            },
            "all": {
                "children": [
                    "group",
                    "ungrouped",
                ]
            },
        }

        data = self.add_key_groups(data)
        return data


    def atlas_graph(self):
        return self.inventory['group']


    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--graph', action = 'store_true')
        self.args = parser.parse_args()


AtlasInventory()
