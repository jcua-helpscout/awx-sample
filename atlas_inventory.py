#!/usr/bin/env python

import argparse
import json
import os
import requests
import sys

from requests.auth import HTTPDigestAuth


class AtlasInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        if self.args.list:
            self.inventory = self.atlas_inventory()
        elif self.args.host:
            self.inventory = self.atlas_inventory()
        else:
            self.inventory = self.atlas_inventory()

        print(json.dumps(self.inventory))


    def atlas_inventory(self):
        auth = HTTPDigestAuth(
            os.getenv('MONGODB_ATLAS_PUBLIC_KEY'),
            os.getenv('MONGODB_ATLAS_PRIVATE_KEY')
        )

        url = 'https://cloud.mongodb.com/api/atlas/v1.0'
        cluster = '/groups/%s/clusters' % (os.getenv('GROUP_ID'))
        result = requests.get('%s%s' % (url, cluster), auth=auth)

        raw_data = { i['name']:i for i in result.json()['results'] }

        data = {
            'group': {
                'hosts': [ i['name'] for i in result.json()['results'] ],
            },
            '_meta': {
                'hostvars': { i['name']:i for i in result.json()['results'] }
            }
        }

        return data


    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()


AtlasInventory()
