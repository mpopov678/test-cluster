import requests, os, dns.resolver
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv
from multidict import MultiDict

load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")


def get_azure_records(resource_group_name: str, zone_name: str):
    dns_client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=resource_group_name,
        zone_name=zone_name,
    )
    azure_rdict = MultiDict()
    supported_types = ["A", "CNAME", "CAA", "SRV", "MX", "TXT"]
    custom_resolver = dns.resolver.Resolver()
    custom_resolver.nameservers = ['8.8.8.8']
    
    for record in record_sets:
        rtype = record.type.split('/')[-1]
        if rtype in supported_types:
            answer = custom_resolver.resolve(record.fqdn, rtype)
            for rdata in answer:
                azure_rdict.add(record.fqdn,  {
                    'fqdn': record.fqdn,
                    'type': rtype,
                    'value': rdata.to_text()
                })

    # print(azure_rdict)

    return(azure_rdict)


def get_technitium_records(zone_name: str):
    url = "http://192.168.88.2:5380/api/zones/records/get"
    technitium_rdict = {}
    params = {
        "token":technitium_api_token,
        'domain':'lab.mpopov.net',
        'listZone':"true",
    }

    response = requests.get(url, params=params).json()
    records = response['response']['records']

    for record in records:
        print('-'*40)
        print(record['name'])
        print(record['type'])
        print(record['rData'])

    return(technitium_rdict)


def get_technitium_a_records():

    url = "http://192.168.88.2:5380/api/zones/records/get"
    dns_store = {}
    params = {
        "token":technitium_api_token,
        'domain':'lab.mpopov.net',
        'listZone':"true",
    }
    
    response = requests.get(url, params=params)
    
    data = response.json()
    records_list = data['response']['records']

    for record in records_list:
        if record.get('type') == 'A':
            ipaddr = record.get('rData')
            name = record.get('name').split('.')[0]
            dns_store[name] = {
                "name": name,
                "type": record.get('type'),
                "ip": ipaddr.get('ipAddress')
            }

    return(dns_store)


def add_technitium_records(AZURE_RECORDS):

    url = "http://192.168.88.2:5380/api/zones/records/add"
    zone = "kenwavesolutions.com"

    for record in AZURE_RECORDS.values():

        params = {
            "token":technitium_api_token,
            'zone':zone,
            'domain':record['fqdn'],
            'type':record['type'],
        }

        if record['type'] == 'A':
            params['ipAddress'] = record['value']

        elif record['type'] == 'CNAME':
            params['cname'] = record['value']

        elif record['type'] == 'TXT':
            params['text'] = record['value']
            params['splitText'] = "true"
            # print(params)

        elif record['type'] == 'CAA':
            print(params)

        elif record['type'] == 'CAA':
            flags, tag, value = record['value'].split()
            params['flags'] = flags
            params['tag'] = tag
            params['value'] = value

        elif record['type'] == 'SRV':
            priority, weight, port, target = record['value'].split()
            params['priority'] = priority
            params['weight'] = weight
            params['port'] = port
            params['target'] = target

        elif record['type'] == 'MX':
            preference, exchange = record['value'].split()
            params['exchange'] = exchange
            params['preference'] = preference

        response = requests.get(url, params=params)
    

if __name__ == "__main__":
    
    RESOURCE_GROUP = "Pipesonik_Resources" 
    ZONE_NAME = "kenwavesolutions.com"
    AZURE_RECORDS = get_azure_records(RESOURCE_GROUP,ZONE_NAME)

    #get_technitium_records('python.com')
    # get_azure_a_records(RESOURCE_GROUP,ZONE_NAME)
    # add_technitium_records(get_azure_records(RESOURCE_GROUP,ZONE_NAME))    
    # get_azure_records(RESOURCE_GROUP,ZONE_NAME)
    add_technitium_records(AZURE_RECORDS)