#!/usr/bin/env python

import argparse
import json
import os
import requests

from requests.auth import HTTPDigestAuth

URL = 'https://cloud.mongodb.com/api/atlas/v1.0'
KEY_GROUPS = [
    'diskSizeGB',
    'mongoDBVersion',
    'providerSettings_diskIOPS',
    'providerSettings_instanceSizeName',
    'providerSettings_volumeType',
    'providerBackupEnabled',
]


class AtlasInventory(object):
    def __init__(self):
        self.auth = HTTPDigestAuth(
            os.getenv('MONGODB_ATLAS_PUBLIC_KEY'),
            os.getenv('MONGODB_ATLAS_PRIVATE_KEY'),
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
        results = {i['id']: i['name'] for i in raw if not i['name'].startswith('v6-')}
        return results

    def add_key_groups(self, data):
        for host in data['_meta']['hostvars']:
            for key_group in KEY_GROUPS:

                # This means this is nested key (parent/child)
                if '_' in key_group:
                    parent_key, child_key = key_group.split('_')
                    label = 'tag_%s_%s' % (
                        key_group,
                        data['_meta']['hostvars'][host][parent_key][child_key],
                    )
                else:
                    label = 'tag_%s_%s' % (
                        key_group,
                        data['_meta']['hostvars'][host][key_group],
                    )

                # Cannot have '.' character in the group name
                label = label.replace('.', '_')

                # Create the new key group otherwise add to the existing one
                if not data.get(label):
                    # Because the 'all' key needs to have the new key group too
                    data['all']['children'].append(label)

                    new_key_group = {label: {'hosts': [host]}}
                    data.update(new_key_group)
                else:
                    data[label]['hosts'].append(host)

        return data

    def atlas_inventory(self):
        raw = []
        for group in self.group_map.keys():
            cluster = '/groups/%s/clusters' % group
            raw.append(requests.get('%s%s' % (URL, cluster), auth=self.auth))

        # The data structure looks like this:
        #   { 'link': [...],
        #     'results': [ { <cluster_1> }, { <cluster_2> } ],
        #     'totalCount: ...
        #   }
        #
        # For each group result, append each element into final_results,
        # so that it will contain all data. Nothing to worry about data
        # being removed because each element is still unique.
        final_result = {'results': []}
        for i, j in enumerate(raw):
            for k in j.json()['results']:
                final_result['results'].append(k)

        data = {
            'group': {
                'hosts': [
                    "%s_%s" % (self.group_map[i['groupId']], i['name'])
                    for i in final_result['results']
                ],
            },
            '_meta': {
                'hostvars': {
                    "%s_%s" % (self.group_map[i['groupId']], i['name']): i
                    for i in final_result['results']
                }
            },
            "all": {"children": []},
        }

        data = self.add_key_groups(data)
        return data

    def atlas_graph(self):
        return self.inventory['group']

    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--graph', action='store_true')
        self.args = parser.parse_args()


AtlasInventory()
