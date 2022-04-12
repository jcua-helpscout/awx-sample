#!/usr/bin/env python

import argparse
import json
import os
import requests

from requests.auth import HTTPDigestAuth
from rich import print as rprint

URL = 'https://cloud.mongodb.com/api/atlas/v1.0'
KEY_GROUPS = ['diskSizeGB', 'groupId', 'mongoDBVersion', 'providerSettings_diskIOPS']


class AtlasInventory(object):
    def __init__(self):
        self.auth = HTTPDigestAuth(
            os.getenv('MONGODB_ATLAS_PUBLIC_KEY'),
            os.getenv('MONGODB_ATLAS_PRIVATE_KEY')
        )

        self.read_cli_args()

        self.group_map = self.get_groups()
        self.inventory = self.atlas_inventory()

        if self.args.graph:
            self.inventory = self.atlas_graph()

        print(json.dumps(self.inventory))


    # Create the group map to translate group id to its actual name
    def get_groups(self):
        raw = requests.get('%s%s' % (URL, '/groups'), auth=self.auth)
        raw = raw.json()['results']
        results = { i['id']:i['name'] for i in raw }
        return results


    def add_key_groups(self, data):
        for host in data['_meta']['hostvars']:
            for key_group in KEY_GROUPS:

                # This means this is nested key (parent/child)
                if '_' in key_group:
                    parent_key, child_key = key_group.split('_')
                    label = 'tag_%s_%s' % (
                        key_group, data['_meta']['hostvars'][host][parent_key][child_key]
                    )
                else:
                    label = 'tag_%s_%s' % (key_group, data['_meta']['hostvars'][host][key_group])

                # Cannot have '.' character in the group name
                label = label.replace('.', '_')

                # Create the new key group otherwise add to the existing one
                if not data.get(label):
                    # Because the 'all' key needs to have the new key group too
                    data['all']['children'].append(label)

                    new_key_group = { label: { 'hosts': [host] } }
                    data.update(new_key_group)
                else:
                    data[label]['hosts'].append(host)

        return data


    def atlas_inventory(self):
        results = []
        for group in os.getenv('GROUP_ID').split(','):
            cluster = '/groups/%s/clusters' % group
            results.append(requests.get('%s%s' % (URL, cluster), auth=self.auth))

#         final_result = {}
#         for i, j in enumerate(results[:-1]):
#             final_result.update(results[i].json() | results[i+1].json())
#
#         import pdb; pdb.set_trace()
#         if len(results) == 1:
#             final_result = results[0].json()

        results[0].json()['results'].extend(results[1].json()['results'])
        final_result = { 'results' : results[0].json() }

        final_result = []
        final_result.append(results[0].json()['results'])
        final_result.append(results[1].json()['results'])

        import pdb; pdb.set_trace()

        data = {
            'group': {
                'hosts': [ "%s_%s" % (self.group_map[i['groupId']], i['name']) for i in final_result['results'] ],
            },
            '_meta': {
                'hostvars': { "%s_%s" % (i['groupId'], i['name']):i for i in final_result['results'] }
            },
            "all": {
                "children": [
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
